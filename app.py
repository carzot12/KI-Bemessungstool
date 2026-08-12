from __future__ import annotations

"""Kompakter V1-Prototyp für manuelle und KI-gestützte Bemessung."""

import threading
import tkinter as tk
from dataclasses import asdict
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image

from ai.assistant import AssistantReply, StabduebelAssistant
from calculations.stabduebel import (
    StabduebelInput,
    StabduebelResult,
    calculate_stabduebel,
)
from calculations.oenorm_validation import ValidationStatus, validate_oenorm
from infopol.materials import (
    KMOD_SOURCE,
    LOAD_DURATION_CLASSES,
    TimberMaterialRepository,
    get_connection_gamma_m,
    get_kmod,
)
from ui import ConnectionVisualizer


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

ASSET_DIR = Path(__file__).resolve().parent / "assets"
LOGO_PATH = ASSET_DIR / "logo.png"


class SplashScreen(ctk.CTkToplevel):
    """Kurzer, reduzierter Startbildschirm für die Desktop-App."""

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)
        self.overrideredirect(True)
        self.configure(fg_color="#FFFFFF")
        self.attributes("-topmost", True)

        width, height = 640, 390
        screen_x = (self.winfo_screenwidth() - width) // 2
        screen_y = (self.winfo_screenheight() - height) // 2
        self.geometry(f"{width}x{height}+{screen_x}+{screen_y}")

        card = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            corner_radius=18,
            border_width=1,
            border_color="#E3E6EA",
        )
        card.pack(fill="both", expand=True, padx=3, pady=3)

        logo = Image.open(LOGO_PATH)
        self.logo_image = ctk.CTkImage(
            light_image=logo,
            dark_image=logo,
            size=(390, 76),
        )
        ctk.CTkLabel(card, text="", image=self.logo_image).pack(pady=(48, 24))
        ctk.CTkLabel(
            card,
            text="KI-Bemessungstool",
            font=ctk.CTkFont(size=27, weight="bold"),
            text_color="#20242A",
        ).pack()
        ctk.CTkLabel(
            card,
            text="KI-gestützte Bemessung von Holzbauverbindungen",
            font=ctk.CTkFont(size=14),
            text_color="#6B7280",
        ).pack(pady=(5, 28))
        ctk.CTkLabel(
            card,
            text="KI-Bemessungstool wird gestartet …",
            font=ctk.CTkFont(size=12),
            text_color="#6B7280",
        ).pack(pady=(0, 10))

        self.progress = ctk.CTkProgressBar(
            card,
            width=400,
            height=8,
            mode="indeterminate",
            progress_color="#B20D30",
            fg_color="#F0D9DF",
        )
        self.progress.pack()
        self.progress.start()
        self.lift()


class StabduebelApp(ctk.CTk):
    RED = "#B20D30"
    RED_DARK = "#890923"
    BG = "#F3F4F6"
    CARD = "#FFFFFF"
    TEXT = "#20242A"
    MUTED = "#6B7280"
    BORDER = "#D9DEE5"
    GREEN = "#228B57"

    MANUAL_FIELDS = (
        ("project_name", "Projektname", "text"),
        ("force_ed_kn", "Bemessungslast Ft,d [kN]", "float"),
        ("width_b_mm", "Breite b [mm]", "float"),
        ("height_h_mm", "Höhe h [mm]", "float"),
        ("number_of_plates_ns", "Anzahl Stahlbleche", "int"),
        ("plate_thickness_ts_mm", "Blechdicke ts [mm]", "float"),
        ("side_thickness_t1_mm", "Seitenholz t1 [mm]", "float"),
        ("middle_thickness_t2_mm", "Mittelholz t2 [mm]", "float"),
        ("slot_air_per_cut_ts_l_mm", "Schlitz-/Luftwert ts,L [mm]", "float"),
        ("dowel_diameter_d_mm", "Stabdübel d [mm]", "float"),
        ("dowel_length_l_mm", "Stabdübellänge l [mm]", "float"),
        ("hole_diameter_d0_mm", "Lochdurchmesser d0 [mm]", "float"),
        ("rows_parallel_n", "Reihen parallel n", "int"),
        ("rows_perpendicular_m", "Reihen quer m", "int"),
        ("a1_mm", "Abstand a1 [mm]", "float"),
        ("a2_mm", "Abstand a2 [mm]", "float"),
        ("a3_t_mm", "Endabstand a3,t [mm]", "float"),
        ("a4_c_mm", "Randabstand a4,c [mm]", "float"),
        ("e1_mm", "Stahlrandabstand e1 [mm]", "float"),
        ("e2_mm", "Stahlrandabstand e2 [mm]", "float"),
        ("kt_e_side", "kt,e Seitenholz [-]", "float"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.withdraw()
        self.title("KI-Bemessungstool")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = int(screen_width * 0.92)
        height = int(screen_height * 0.90)
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min(1120, screen_width), min(720, screen_height))
        self.after(0, self._maximize_window)
        self.configure(fg_color=self.BG)

        self.materials = TimberMaterialRepository()
        self.assistant = StabduebelAssistant()
        self.entries: dict[str, ctk.CTkEntry] = {}
        self.timber_grade = tk.StringVar(value=StabduebelInput().timber_grade)
        self.manual_service_class = tk.StringVar(value="1")
        self.manual_load_duration = tk.StringVar(value="mittel")
        self.manual_kmod_text = tk.StringVar(value="automatisch: 0,80")
        self.workspace_mode = tk.StringVar(value="✦ KI Workspace")

        self._build_header()
        self._build_tabs()
        self._load_manual_defaults()

    def _maximize_window(self) -> None:
        try:
            self.state("zoomed")
        except tk.TclError:
            try:
                self.attributes("-zoomed", True)
            except tk.TclError:
                pass

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, height=92, corner_radius=0, fg_color=self.CARD)
        header.pack(fill="x")
        header.pack_propagate(False)

        logo = Image.open(LOGO_PATH)
        self.header_logo_image = ctk.CTkImage(
            light_image=logo,
            dark_image=logo,
            size=(205, 40),
        )
        ctk.CTkLabel(header, text="", image=self.header_logo_image).pack(
            side="left", padx=(28, 25), pady=20
        )

        heading = ctk.CTkFrame(header, fg_color="transparent")
        heading.pack(side="left", fill="y")
        ctk.CTkLabel(
            heading,
            text="KI-Bemessungstool",
            font=ctk.CTkFont(size=25, weight="bold"),
            text_color=self.TEXT,
        ).pack(anchor="w", pady=(18, 2))
        ctk.CTkLabel(
            heading,
            text="KI-gestützte Bemessung von Holzbauverbindungen",
            font=ctk.CTkFont(size=13),
            text_color=self.MUTED,
        ).pack(anchor="w")

        status = ctk.CTkFrame(header, fg_color="transparent")
        status.pack(side="right", padx=28)
        ctk.CTkLabel(
            status, text="NORMMODUS", text_color=self.MUTED,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(anchor="e")
        ctk.CTkLabel(
            status, text="ÖNORM", text_color=self.RED,
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="e")
        self.header_ai_status = ctk.CTkLabel(
            status, text="○ KI BEREIT", text_color=self.MUTED,
            font=ctk.CTkFont(size=11),
        )
        self.header_ai_status.pack(anchor="e", pady=(4, 0))

        self.mode_switch = ctk.CTkSegmentedButton(
            header,
            values=["✦ KI Workspace", "Kompakt", "Manuell"],
            variable=self.workspace_mode,
            command=self._show_mode,
            selected_color=self.RED,
            selected_hover_color=self.RED_DARK,
            unselected_color="#E5E7EB",
            unselected_hover_color="#D8DCE1",
            text_color=self.TEXT,
            width=390,
            height=34,
        )
        self.mode_switch.place(relx=0.57, rely=0.5, anchor="center")

    def _build_tabs(self) -> None:
        self.workspace_container = ctk.CTkFrame(self, fg_color=self.BG)
        self.workspace_container.pack(fill="both", expand=True, padx=18, pady=12)
        self.workspace_container.grid_rowconfigure(0, weight=1)
        self.workspace_container.grid_columnconfigure(0, weight=1)
        self.mode_frames: dict[str, ctk.CTkFrame] = {}
        for name in ("✦ KI Workspace", "Kompakt", "Manuell"):
            frame = ctk.CTkFrame(self.workspace_container, fg_color=self.BG)
            frame.grid(row=0, column=0, sticky="nsew")
            self.mode_frames[name] = frame
        self._build_assistant_tab(self.mode_frames["✦ KI Workspace"])
        self._build_compact_tab(self.mode_frames["Kompakt"])
        self._build_manual_tab(self.mode_frames["Manuell"])
        self._show_mode("✦ KI Workspace")

    def _show_mode(self, mode: str) -> None:
        if mode not in self.mode_frames:
            return
        self.workspace_mode.set(mode)
        if mode == "Manuell" and self.assistant.state.last_result is not None:
            data = self.assistant.state.last_result.input
            self.timber_grade.set(data.timber_grade)
            self.manual_service_class.set(str(data.service_class))
            self.manual_load_duration.set(data.load_duration_class)
            for key, entry in self.entries.items():
                if hasattr(data, key):
                    entry.delete(0, "end")
                    entry.insert(0, str(getattr(data, key)))
        self.mode_frames[mode].tkraise()

    def _select_workspace_section(self, section: str) -> None:
        for label, button in self.sidebar_buttons.items():
            active = label == section
            button.configure(
                fg_color="#FFFFFF" if active else "transparent",
                text_color=self.RED if active else self.TEXT,
                text=("●" if active else "○") + f"  {label}",
            )
        messages = {
            "Entwurf": "Aktueller Entwurf und KI-Entscheidungen.",
            "Varianten": "Die vertiefte Variantenansicht folgt in Phase 2. Reale Varianten bleiben im aktuellen Optimierungsergebnis verfügbar.",
            "Nachweise": "Alle vorhandenen Einzelnachweise stehen im scrollbaren Ergebnisbereich rechts.",
            "Quellen": "Verwendete Knowledge-Base-Quellen werden im Bereich Technische Einordnung angezeigt.",
            "Bericht": "Die Berichtsvorschau wird in Phase 2 ergänzt; es wird noch kein neuer Bericht erzeugt.",
        }
        self.technical_explanation.configure(text=messages[section])

    def _build_assistant_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=0, minsize=190)
        tab.grid_columnconfigure(1, weight=6, minsize=430)
        tab.grid_columnconfigure(2, weight=5, minsize=410)
        tab.grid_rowconfigure(0, weight=5)
        tab.grid_rowconfigure(1, weight=2)
        tab.grid_rowconfigure(2, weight=5)

        sidebar = ctk.CTkFrame(tab, width=196, fg_color="#ECEEF1", corner_radius=14)
        sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 8), pady=6)
        sidebar.grid_propagate(False)
        ctk.CTkLabel(
            sidebar, text="PROJEKT", text_color=self.MUTED,
            font=ctk.CTkFont(size=10, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(22, 10))
        self.sidebar_buttons: dict[str, ctk.CTkButton] = {}
        for index, (label, symbol) in enumerate((
            ("Entwurf", "●"), ("Varianten", "○"), ("Nachweise", "○"),
            ("Quellen", "○"), ("Bericht", "○"),
        )):
            button = ctk.CTkButton(
                sidebar, text=f"{symbol}  {label}", anchor="w", height=38,
                fg_color="#FFFFFF" if index == 0 else "transparent",
                hover_color="#FFFFFF", text_color=self.RED if index == 0 else self.TEXT,
                command=lambda item=label: self._select_workspace_section(item),
            )
            button.pack(fill="x", padx=10, pady=2)
            self.sidebar_buttons[label] = button
        ctk.CTkLabel(
            sidebar,
            text="Zuglaschenstoß\nStabdübel · Zug",
            justify="left", text_color=self.MUTED,
            font=ctk.CTkFont(size=10),
        ).pack(side="bottom", anchor="w", padx=18, pady=20)

        chat_card = ctk.CTkFrame(tab, fg_color=self.CARD, corner_radius=14)
        chat_card.grid(row=0, column=1, sticky="nsew", padx=8, pady=(6, 4))
        chat_card.grid_columnconfigure(0, weight=1)
        chat_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            chat_card,
            text="✦ KI Copilot",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 8))

        self.chat = ctk.CTkTextbox(
            chat_card,
            wrap="word",
            font=ctk.CTkFont(size=14),
            fg_color="#F8F9FA",
            border_width=1,
            border_color=self.BORDER,
        )
        self.chat.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 12))
        self.chat.insert(
            "end",
            "✦ KI\nBeschreibe Last, Holzklasse und Entwurfsziel. "
            "Zum Beispiel: ‚Bemesse einen Stabdübelanschluss für 140 kN mit "
            "GL24h und möglichst wenigen Stabdübeln.‘\n\n",
        )
        self.chat.configure(state="disabled")
        self.chat._textbox.tag_configure(  # type: ignore[attr-defined]
            "user_message", background="#F0F1F3", foreground=self.TEXT,
            lmargin1=18, lmargin2=18, rmargin=70, spacing1=8, spacing3=12,
        )
        self.chat._textbox.tag_add("ai_message", "1.0", "end")  # type: ignore[attr-defined]
        self.chat._textbox.tag_configure(  # type: ignore[attr-defined]
            "ai_message", background="#FFFFFF", foreground=self.TEXT,
            lmargin1=18, lmargin2=18, rmargin=28, spacing1=8, spacing3=14,
        )
        self.chat.bind("<B1-Motion>", self._chat_selection_autoscroll, add="+")
        self.chat.bind("<Command-c>", self._copy_chat_selection)
        self.chat.bind("<Control-c>", self._copy_chat_selection)

        self.new_message_button = ctk.CTkButton(
            chat_card, text="↓ Neue Nachricht", width=145, height=28,
            fg_color="#E9ECEF", hover_color="#DDE1E5", text_color=self.TEXT,
            command=self._scroll_chat_to_end,
        )
        self.new_message_button.grid(row=2, column=0, sticky="e", padx=20, pady=(0, 6))
        self.new_message_button.grid_remove()

        self.engineering_status = ctk.CTkLabel(
            chat_card,
            text="",
            justify="left", anchor="w", text_color=self.MUTED,
            fg_color="#F6F7F8", corner_radius=10,
            font=ctk.CTkFont(size=11),
        )
        self.engineering_status.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.engineering_status.grid_remove()

        input_row = ctk.CTkFrame(chat_card, fg_color="transparent")
        input_row.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 18))
        input_row.grid_columnconfigure(0, weight=1)
        self.assistant_entry = ctk.CTkTextbox(
            input_row,
            height=72,
            wrap="word",
            font=ctk.CTkFont(size=14),
            border_color=self.BORDER,
            border_width=1,
            fg_color="#FFFFFF",
        )
        self.assistant_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._chat_placeholder = "Beschreibe deinen Anschluss oder frag die KI …"
        self.assistant_entry.insert("1.0", self._chat_placeholder)
        self.assistant_entry.configure(text_color=self.MUTED)
        self.assistant_entry.bind("<FocusIn>", self._clear_chat_placeholder, add="+")
        self.assistant_entry.bind("<Return>", self._on_chat_enter)
        self.assistant_entry.bind("<Shift-Return>", self._on_chat_shift_enter)
        self.send_button = ctk.CTkButton(
            input_row,
            text="↑",
            width=52,
            height=52,
            corner_radius=18,
            fg_color=self.RED,
            hover_color=self.RED_DARK,
            command=self._send_to_assistant,
        )
        self.send_button.grid(row=0, column=1)

        technical_panel = ctk.CTkFrame(tab, fg_color=self.CARD, corner_radius=14)
        technical_panel.grid(
            row=1, column=1, rowspan=2, sticky="nsew", padx=8, pady=(4, 6)
        )
        technical_panel.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            technical_panel, text="Technische Einordnung",
            font=ctk.CTkFont(size=17, weight="bold"), text_color=self.TEXT,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(15, 5))
        self.technical_classification = ctk.CTkLabel(
            technical_panel, text="Noch keine technischen Werte.",
            justify="left", anchor="nw", text_color=self.TEXT,
            font=ctk.CTkFont(size=11),
        )
        self.technical_classification.grid(row=1, column=0, sticky="ew", padx=18)
        ctk.CTkLabel(
            technical_panel, text="Warum? / Erklärung",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=self.TEXT,
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(10, 2))
        self.technical_explanation = ctk.CTkLabel(
            technical_panel, text="–", justify="left", anchor="w",
            wraplength=510, text_color=self.MUTED, font=ctk.CTkFont(size=10),
        )
        self.technical_explanation.grid(row=3, column=0, sticky="ew", padx=18)
        self.technical_source = ctk.CTkLabel(
            technical_panel, text="Quelle: –", justify="left", anchor="w",
            wraplength=510, text_color=self.MUTED, font=ctk.CTkFont(size=9),
        )
        self.technical_source.grid(row=4, column=0, sticky="ew", padx=18, pady=(5, 14))

        self.ai_visualizer = ConnectionVisualizer(tab)
        self.ai_visualizer.grid(
            row=0, column=2, sticky="nsew", padx=(8, 0), pady=(6, 4)
        )

        current_design = ctk.CTkFrame(tab, fg_color=self.CARD, corner_radius=14)
        current_design.grid(row=1, column=2, sticky="nsew", padx=(8, 0), pady=4)
        ctk.CTkLabel(
            current_design, text="AKTUELLER ENTWURF",
            font=ctk.CTkFont(size=10, weight="bold"), text_color=self.MUTED,
        ).pack(anchor="w", padx=16, pady=(12, 4))
        self.current_design_summary = ctk.CTkLabel(
            current_design, text="Noch kein berechneter Entwurf.",
            justify="left", anchor="w", text_color=self.TEXT,
            font=ctk.CTkFont(size=11),
        )
        self.current_design_summary.pack(fill="x", padx=16, pady=(0, 12))

        result_card = ctk.CTkScrollableFrame(tab, fg_color=self.CARD, corner_radius=14)
        result_card.grid(row=2, column=2, sticky="nsew", padx=(8, 0), pady=(4, 6))
        result_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            result_card,
            text="Berechnungsergebnis",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 5))
        self.ai_mode_label = ctk.CTkLabel(
            result_card,
            text="Bereit",
            font=ctk.CTkFont(size=11),
            text_color=self.MUTED,
        )
        self.ai_mode_label.grid(row=1, column=0, sticky="w", padx=20)

        self.recognized_values = ctk.CTkLabel(
            result_card,
            text="Noch keine Vorgaben erkannt.",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=self.MUTED,
        )
        self.recognized_values.grid(row=3, column=0, sticky="ew", padx=20)
        self.recognized_values.grid_remove()

        self.ai_status_frame = ctk.CTkFrame(
            result_card,
            fg_color="#EEF1F4",
            corner_radius=12,
            border_width=1,
            border_color=self.BORDER,
        )
        self.ai_status_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(14, 8))
        self.ai_status_frame.grid_columnconfigure(0, weight=1)
        self.ai_status_title = ctk.CTkLabel(
            self.ai_status_frame,
            text="NOCH KEIN NACHWEIS",
            font=ctk.CTkFont(size=17, weight="bold"),
            text_color=self.MUTED,
        )
        self.ai_status_title.grid(row=0, column=0, sticky="w", padx=16, pady=(13, 3))
        self.ai_eta_label = ctk.CTkLabel(
            self.ai_status_frame,
            text="η = –",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=self.MUTED,
        )
        self.ai_eta_label.grid(row=1, column=0, sticky="w", padx=16)
        self.ai_status_details = ctk.CTkLabel(
            self.ai_status_frame,
            text="",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT,
        )
        self.ai_status_details.grid(row=2, column=0, sticky="ew", padx=16)
        self.ai_utilization_bar = ctk.CTkProgressBar(
            self.ai_status_frame,
            height=12,
            progress_color=self.MUTED,
            fg_color="#D8DDE3",
        )
        self.ai_utilization_bar.grid(row=3, column=0, sticky="ew", padx=16, pady=(9, 14))
        self.ai_utilization_bar.set(0)

        ctk.CTkLabel(
            result_card,
            text="Technisches Ergebnis",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=5, column=0, sticky="w", padx=20, pady=(5, 3))
        self.ai_result = ctk.CTkTextbox(
            result_card,
            height=270,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12),
            fg_color="#F8F9FA",
            border_width=1,
            border_color=self.BORDER,
        )
        self.ai_result.grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.ai_result.configure(state="disabled")

        ctk.CTkLabel(
            result_card,
            text="KI-Auswertung & Empfehlung",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=7, column=0, sticky="w", padx=20, pady=(3, 3))
        self.ai_interpretation = ctk.CTkTextbox(
            result_card,
            height=115,
            wrap="word",
            font=ctk.CTkFont(size=11),
            fg_color="#F8F9FA",
            border_width=1,
            border_color=self.BORDER,
        )
        self.ai_interpretation.grid(row=8, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.ai_interpretation.configure(state="disabled")
        actions = ctk.CTkFrame(result_card, fg_color="transparent")
        actions.grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 8))
        for column in range(3):
            actions.grid_columnconfigure(column, weight=1)
        ctk.CTkButton(
            actions, text="Alle Nachweise", height=32,
            fg_color="#E9ECEF", hover_color="#DDE1E5", text_color=self.TEXT,
            command=lambda: self.ai_result.focus_set(),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            actions, text="Varianten", height=32,
            fg_color="#E9ECEF", hover_color="#DDE1E5", text_color=self.TEXT,
            command=lambda: self.assistant_entry.insert("end", "Zeig mir Varianten"),
        ).grid(row=0, column=1, sticky="ew", padx=4)
        ctk.CTkButton(
            actions, text="Bericht exportieren", height=32, state="disabled",
            fg_color="#E9ECEF", text_color=self.MUTED,
        ).grid(row=0, column=2, sticky="ew", padx=(4, 0))
        ctk.CTkButton(
            result_card,
            text="Dialog zurücksetzen",
            fg_color="#E9ECEF",
            hover_color="#DDE1E5",
            text_color=self.TEXT,
            command=self._reset_assistant,
        ).grid(row=10, column=0, sticky="ew", padx=20, pady=(0, 18))

    def _build_compact_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=4)
        tab.grid_columnconfigure(1, weight=6)
        tab.grid_rowconfigure(0, weight=1)
        self.compact_force = tk.StringVar(value="140")
        self.compact_grade = tk.StringVar(value="GL24h")
        self.compact_width = tk.StringVar(value="200")
        self.compact_height = tk.StringVar(value="240")
        self.compact_service = tk.StringVar(value="1")
        self.compact_duration = tk.StringVar(value="mittel")
        self.compact_goal = tk.StringVar(value="wenig Stabdübel")

        form = ctk.CTkFrame(tab, fg_color=self.CARD, corner_radius=16)
        form.grid(row=0, column=0, sticky="nsew", padx=(6, 8), pady=6)
        form.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            form, text="Zuglaschenstoß", font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(24, 4))
        ctk.CTkLabel(
            form, text="Schnelle KI-gestützte Vorbemessung", text_color=self.MUTED,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 18))
        fields = (
            ("FEd [kN]", self.compact_force, None),
            ("Holzklasse", self.compact_grade, list(self.materials.grades())),
            ("Breite b [mm]", self.compact_width, None),
            ("Höhe h [mm]", self.compact_height, None),
            ("Nutzungsklasse", self.compact_service, ["1", "2", "3"]),
            ("Lasteinwirkungsdauer", self.compact_duration, list(LOAD_DURATION_CLASSES)),
        )
        for row, (label, variable, values) in enumerate(fields, start=2):
            ctk.CTkLabel(form, text=label, anchor="w", text_color=self.TEXT).grid(
                row=row, column=0, sticky="w", padx=24, pady=7
            )
            widget = (
                ctk.CTkComboBox(form, variable=variable, values=values, state="readonly")
                if values else ctk.CTkEntry(form, textvariable=variable)
            )
            widget.grid(row=row, column=1, sticky="ew", padx=(12, 24), pady=7)
        ctk.CTkLabel(form, text="Optimierungsziel", text_color=self.TEXT).grid(
            row=8, column=0, sticky="w", padx=24, pady=(18, 7)
        )
        ctk.CTkSegmentedButton(
            form, values=["wenig Stabdübel", "mehr Reserve", "kompakt"],
            variable=self.compact_goal, selected_color=self.RED,
        ).grid(row=9, column=0, columnspan=2, sticky="ew", padx=24, pady=7)
        ctk.CTkButton(
            form, text="✦ KI optimieren", height=46, fg_color=self.RED,
            hover_color=self.RED_DARK, command=self._run_compact,
        ).grid(row=10, column=0, columnspan=2, sticky="ew", padx=24, pady=(20, 10))
        ctk.CTkButton(
            form, text="Weitere Einstellungen  ›", height=34,
            fg_color="transparent", hover_color="#F2F3F5", text_color=self.TEXT,
            command=lambda: self._show_mode("Manuell"),
        ).grid(row=11, column=0, columnspan=2, sticky="ew", padx=24, pady=(0, 20))

        right = ctk.CTkFrame(tab, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 6), pady=6)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=3)
        right.grid_rowconfigure(1, weight=2)
        self.compact_visualizer = ConnectionVisualizer(right)
        self.compact_visualizer.grid(row=0, column=0, sticky="nsew", pady=(0, 5))
        result = ctk.CTkFrame(right, fg_color=self.CARD, corner_radius=16)
        result.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        self.compact_result = ctk.CTkLabel(
            result, text="Noch kein Ergebnis", justify="left", anchor="nw",
            text_color=self.MUTED, font=ctk.CTkFont(size=15),
        )
        self.compact_result.pack(fill="both", expand=True, padx=24, pady=22)

    def _run_compact(self) -> None:
        goal = {
            "wenig Stabdübel": "möglichst wenige Stabdübel",
            "mehr Reserve": "mehr Reserve",
            "kompakt": "möglichst kompakte Geometrie",
        }[self.compact_goal.get()]
        prompt = (
            f"{self.compact_force.get()} kN {self.compact_grade.get()} "
            f"{self.compact_width.get()}x{self.compact_height.get()} mm "
            f"NK{self.compact_service.get()} {self.compact_duration.get()}, "
            f"{goal}, rest mach selber"
        )
        self._append_chat("Du", prompt)
        reply = self.assistant.respond(prompt)
        self._show_assistant_reply(reply)
        if reply.result:
            result = reply.result
            data = result.input
            status = "✓ NACHWEIS ERFÜLLT" if validate_oenorm(data, result).admissible else "✕ NICHT ERFÜLLT"
            self.compact_result.configure(
                text=(
                    f"{status}\n\nη = {result.governing_check.utilization:.0%}\n"
                    f"Maßgebend: {result.governing_check.name}\n\n"
                    f"{data.rows_parallel_n} × {data.rows_perpendicular_m} = "
                    f"{data.rows_parallel_n * data.rows_perpendicular_m} Stabdübel · "
                    f"Ø{data.dowel_diameter_d_mm:g} mm"
                ),
                text_color=self.GREEN if validate_oenorm(data, result).admissible else self.RED,
            )
            self.compact_visualizer.update_input(data, result)

    def _build_manual_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=2)
        tab.grid_columnconfigure(1, weight=3)
        tab.grid_rowconfigure(0, weight=1)

        form = ctk.CTkScrollableFrame(
            tab,
            label_text="Eingabedaten",
            label_font=ctk.CTkFont(size=18, weight="bold"),
            fg_color=self.CARD,
            corner_radius=14,
        )
        form.grid(row=0, column=0, sticky="nsew", padx=(8, 10), pady=10)
        form.grid_columnconfigure(0, weight=1)

        self._manual_material_row(form)
        self._manual_design_condition_rows(form)
        row = 4
        section_starts = {
            "project_name": "ALLGEMEIN",
            "width_b_mm": "HOLZQUERSCHNITT",
            "number_of_plates_ns": "ANSCHLUSSAUFBAU",
            "dowel_diameter_d_mm": "STABDÜBEL UND ABSTÄNDE",
        }
        for key, label, kind in self.MANUAL_FIELDS:
            if key in section_starts:
                ctk.CTkLabel(
                    form,
                    text=section_starts[key],
                    text_color=self.RED,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    anchor="w",
                ).grid(row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(15, 4))
                row += 1
            ctk.CTkLabel(form, text=label, text_color=self.TEXT, anchor="w").grid(
                row=row, column=0, sticky="w", padx=12, pady=5
            )
            entry = ctk.CTkEntry(form, width=170, border_color=self.BORDER)
            entry.grid(row=row, column=1, sticky="e", padx=12, pady=5)
            entry._value_kind = kind  # type: ignore[attr-defined]
            self.entries[key] = entry
            row += 1

        ctk.CTkLabel(
            form,
            text=(
                "Die geladenen Startwerte bilden den bestehenden Referenzfall ab. "
                "Sie sind keine allgemeingültigen Norm-Standardwerte."
            ),
            wraplength=360,
            justify="left",
            text_color=self.MUTED,
            font=ctk.CTkFont(size=10),
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 4))
        button_row = row + 1
        ctk.CTkButton(
            form,
            text="Nachweis berechnen",
            height=44,
            fg_color=self.RED,
            hover_color=self.RED_DARK,
            command=self._calculate_manual,
        ).grid(row=button_row, column=0, columnspan=2, sticky="ew", padx=12, pady=(16, 6))
        ctk.CTkButton(
            form,
            text="Standardwerte laden",
            fg_color="#E9ECEF",
            hover_color="#DDE1E5",
            text_color=self.TEXT,
            command=self._load_manual_defaults,
        ).grid(row=button_row + 1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 16))

        manual_right = ctk.CTkFrame(tab, fg_color="transparent")
        manual_right.grid(row=0, column=1, sticky="nsew", padx=(10, 8), pady=10)
        manual_right.grid_columnconfigure(0, weight=1)
        manual_right.grid_rowconfigure(0, weight=4)
        manual_right.grid_rowconfigure(1, weight=5)

        self.manual_visualizer = ConnectionVisualizer(manual_right)
        self.manual_visualizer.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        result = ctk.CTkFrame(manual_right, fg_color=self.CARD, corner_radius=14)
        result.grid(row=1, column=0, sticky="nsew", pady=(5, 0))
        result.grid_columnconfigure(0, weight=1)
        result.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(
            result,
            text="Ergebnisse des Rechenkerns",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 8))

        self.manual_status_frame = ctk.CTkFrame(
            result,
            fg_color="#EEF1F4",
            corner_radius=12,
            border_width=1,
            border_color=self.BORDER,
        )
        self.manual_status_frame.grid(
            row=1, column=0, sticky="ew", padx=20, pady=(4, 12)
        )
        self.manual_status_frame.grid_columnconfigure(0, weight=1)
        self.manual_status_title = ctk.CTkLabel(
            self.manual_status_frame,
            text="NOCH KEIN NACHWEIS",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.MUTED,
        )
        self.manual_status_title.grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 5)
        )
        self.manual_eta_label = ctk.CTkLabel(
            self.manual_status_frame,
            text="η = –",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=self.MUTED,
        )
        self.manual_eta_label.grid(row=1, column=0, sticky="w", padx=18)
        self.manual_status_details = ctk.CTkLabel(
            self.manual_status_frame,
            text="Nach der Berechnung erscheint hier die Zusammenfassung.",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=self.MUTED,
        )
        self.manual_status_details.grid(
            row=2, column=0, sticky="ew", padx=18
        )
        self.manual_utilization_bar = ctk.CTkProgressBar(
            self.manual_status_frame,
            height=13,
            progress_color=self.MUTED,
            fg_color="#D8DDE3",
        )
        self.manual_utilization_bar.grid(
            row=3, column=0, sticky="ew", padx=18, pady=(11, 17)
        )
        self.manual_utilization_bar.set(0)

        ctk.CTkLabel(
            result,
            text="Detaillierte Einzelnachweise",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(0, 5))
        self.manual_result = ctk.CTkTextbox(
            result,
            font=ctk.CTkFont(family="Courier", size=12),
            fg_color="#F8F9FA",
            border_width=1,
            border_color=self.BORDER,
        )
        self.manual_result.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.manual_result.configure(state="disabled")

    def _manual_material_row(self, form: ctk.CTkScrollableFrame) -> None:
        ctk.CTkLabel(form, text="Holzfestigkeitsklasse", text_color=self.TEXT).grid(
            row=0, column=0, sticky="w", padx=12, pady=5
        )
        ctk.CTkComboBox(
            form,
            width=170,
            values=list(self.materials.grades()),
            variable=self.timber_grade,
            state="readonly",
            border_color=self.BORDER,
            command=lambda _value: self._update_manual_kmod(),
        ).grid(row=0, column=1, sticky="e", padx=12, pady=5)

    def _manual_design_condition_rows(self, form: ctk.CTkScrollableFrame) -> None:
        for row, label in ((1, "Nutzungsklasse"), (2, "Lasteinwirkungsdauer"), (3, "kmod")):
            ctk.CTkLabel(form, text=label, text_color=self.TEXT, anchor="w").grid(
                row=row, column=0, sticky="w", padx=12, pady=5
            )
        ctk.CTkComboBox(
            form,
            width=170,
            values=["1", "2", "3"],
            variable=self.manual_service_class,
            state="readonly",
            border_color=self.BORDER,
            command=lambda _value: self._update_manual_kmod(),
        ).grid(row=1, column=1, sticky="e", padx=12, pady=5)
        ctk.CTkComboBox(
            form,
            width=170,
            values=list(LOAD_DURATION_CLASSES),
            variable=self.manual_load_duration,
            state="readonly",
            border_color=self.BORDER,
            command=lambda _value: self._update_manual_kmod(),
        ).grid(row=2, column=1, sticky="e", padx=12, pady=5)
        ctk.CTkLabel(
            form,
            textvariable=self.manual_kmod_text,
            text_color=self.MUTED,
            anchor="e",
        ).grid(row=3, column=1, sticky="e", padx=12, pady=5)

    def _update_manual_kmod(self) -> float:
        material = self.materials.get(self.timber_grade.get())
        value = get_kmod(
            material,
            int(self.manual_service_class.get()),
            self.manual_load_duration.get(),
        )
        self.manual_kmod_text.set(f"automatisch: {value:.2f}".replace(".", ","))
        return value

    def _send_to_assistant(self) -> None:
        text = self.assistant_entry.get("1.0", "end-1c").strip()
        if not text or text == self._chat_placeholder:
            return
        self.assistant_entry.delete("1.0", "end")
        self.assistant_entry.focus_set()
        self._append_chat("Sie", text)
        self.send_button.configure(state="disabled", text="…")
        self.engineering_status.configure(
            text=(
                "✦ Entwurf wird untersucht\n"
                "Geometrie  ✓    Material  ✓    Stabdübel  ●\n"
                "Blechvarianten  ●    ÖNORM-Prüfung  ○    Ranking  ○"
            )
        )
        self.engineering_status.grid()
        self.ai_mode_label.configure(text="Anfrage wird verarbeitet …")
        self.header_ai_status.configure(text="KI · verarbeitet …", text_color=self.RED)
        threading.Thread(target=self._assistant_worker, args=(text,), daemon=True).start()

    def _assistant_worker(self, text: str) -> None:
        try:
            reply = self.assistant.respond(text)
            self.after(0, lambda: self._show_assistant_reply(reply))
        except Exception as exc:
            self.after(0, lambda: self._show_assistant_error(str(exc)))

    def _show_assistant_reply(self, reply: AssistantReply) -> None:
        self._append_chat("Assistent", reply.text)
        mode = "OpenAI LLM + deterministischer Rechenkern" if reply.used_llm else (
            "KI-Sprachmodell nicht verfügbar – eingeschränkter lokaler Modus"
        )
        self.ai_mode_label.configure(text=mode)
        self.header_ai_status.configure(
            text="● KI ONLINE" if reply.used_llm else "○ LOKALER MODUS",
            text_color=self.GREEN if reply.used_llm else self.MUTED,
        )
        self.recognized_values.configure(
            text=reply.recognized_parameters or "Noch keine Vorgaben erkannt."
        )
        self._update_technical_classification(reply)
        self._set_text(self.ai_interpretation, reply.interpretation)
        if reply.result:
            self._set_text(self.ai_result, self._detailed_result(reply.result))
            self._update_status_block(reply.result)
            self.ai_visualizer.update_input(reply.result.input, reply.result)
        else:
            self._clear_status_block()
        optimization = self.assistant.state.last_optimization
        if optimization is not None:
            self.engineering_status.configure(
                text=(
                    f"✓ {optimization.evaluated_count} Varianten analysiert\n"
                    f"✓ {optimization.feasible_count} zulässige Varianten\n"
                    + ("✓ beste Variante ausgewählt" if optimization.selected else "○ keine geeignete Variante ausgewählt")
                ),
                text_color=self.GREEN if optimization.selected else self.RED,
            )
            self.engineering_status.grid()
        else:
            self.engineering_status.grid_remove()
        self.send_button.configure(state="normal", text="↑")
        self.assistant_entry.focus_set()

    def _show_assistant_error(self, error: str) -> None:
        self._append_chat("Fehler", error)
        self.ai_mode_label.configure(text="Fehler")
        self.header_ai_status.configure(text="✕ KI-FEHLER", text_color=self.RED)
        self.engineering_status.grid_remove()
        self.send_button.configure(state="normal", text="↑")
        self.assistant_entry.focus_set()

    def _reset_assistant(self) -> None:
        self.assistant.reset()
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.insert("end", "✦ KI\nNeuer Entwurfsdialog gestartet.\n\n", "ai_message")
        self.chat.configure(state="disabled")
        self._set_text(self.ai_result, "")
        self._set_text(self.ai_interpretation, "")
        self.recognized_values.configure(text="Noch keine Vorgaben erkannt.")
        self.technical_classification.configure(text="Noch keine technischen Werte.")
        self.technical_explanation.configure(text="–")
        self.technical_source.configure(text="Quelle: –")
        self.current_design_summary.configure(text="Noch kein berechneter Entwurf.")
        self._clear_status_block()
        self.ai_visualizer.clear()
        self.ai_mode_label.configure(text="Bereit")
        self.header_ai_status.configure(text="○ KI BEREIT", text_color=self.MUTED)

    def _update_technical_classification(self, reply: AssistantReply) -> None:
        state = self.assistant.state
        result_input = reply.result.input if reply.result else None
        values = dict(state.parameters)
        if result_input is not None:
            values.update({
                "service_class": result_input.service_class,
                "load_duration_class": result_input.load_duration_class,
                "number_of_plates_ns": result_input.number_of_plates_ns,
                "plate_thickness_ts_mm": result_input.plate_thickness_ts_mm,
                "side_thickness_t1_mm": result_input.side_thickness_t1_mm,
                "middle_thickness_t2_mm": result_input.middle_thickness_t2_mm,
                "dowel_diameter_d_mm": result_input.dowel_diameter_d_mm,
                "rows_parallel_n": result_input.rows_parallel_n,
                "rows_perpendicular_m": result_input.rows_perpendicular_m,
            })
        provenance_labels = {
            "USER_FIXED": "Benutzervorgabe",
            "KNOWLEDGE_DERIVED": "KI-Einordnung",
            "DERIVED": "abgeleitet",
            "OPTIMIZED": "optimiert",
        }

        def origin(key: str, default: str = "DERIVED") -> str:
            code = state.parameter_provenance.get(key, default)
            return provenance_labels.get(code, code)

        rows: list[str] = []
        if "service_class" in values:
            rows.append(f"Nutzungsklasse: {values['service_class']}  ·  {origin('service_class')}")
        if "load_duration_class" in values:
            rows.append(
                f"Lasteinwirkungsdauer: {values['load_duration_class']}  ·  "
                f"{origin('load_duration_class')}"
            )
        if result_input is not None:
            rows.append(f"kmod: {result_input.k_mod:g}  ·  abgeleitet")
            rows.append(f"Anschlussaufbau: {result_input.connection_case}  ·  {origin('number_of_plates_ns', 'OPTIMIZED')}")
        if "number_of_plates_ns" in values:
            rows.append(f"Blechanzahl: {values['number_of_plates_ns']}  ·  {origin('number_of_plates_ns', 'OPTIMIZED')}")
        for key, label in (
            ("plate_thickness_ts_mm", "Blechdicke ts"),
            ("side_thickness_t1_mm", "Seitenholz t1"),
            ("middle_thickness_t2_mm", "Mittelholz t2"),
            ("dowel_diameter_d_mm", "Durchmesser"),
        ):
            if key in values:
                rows.append(f"{label}: {float(values[key]):g} mm  ·  {origin(key, 'OPTIMIZED')}")
        if {"rows_parallel_n", "rows_perpendicular_m"} <= values.keys():
            n, m = int(values["rows_parallel_n"]), int(values["rows_perpendicular_m"])
            rows.append(f"Anordnung: {n} × {m} = {n*m}  ·  {origin('rows_parallel_n', 'OPTIMIZED')}")
        self.technical_classification.configure(
            text="\n".join(rows) if rows else "Noch keine technischen Werte."
        )
        explanation = state.current_explanation or reply.interpretation or "–"
        self.technical_explanation.configure(text=explanation)
        sources = list(dict.fromkeys(state.parameter_sources.values()))
        if result_input is not None:
            sources.append(KMOD_SOURCE)
            self.current_design_summary.configure(
                text=(
                    f"{result_input.force_ed_kn:g} kN     {result_input.timber_grade}     "
                    f"{result_input.width_b_mm:g} × {result_input.height_h_mm:g} mm     "
                    f"NK{result_input.service_class} · {result_input.load_duration_class} · "
                    f"kmod {result_input.k_mod:g}\n"
                    f"{result_input.number_of_plates_ns} Bleche · {result_input.plate_thickness_ts_mm:g} mm     "
                    f"t1 {result_input.side_thickness_t1_mm:g} · t2 {result_input.middle_thickness_t2_mm:g} mm     "
                    f"Ø{result_input.dowel_diameter_d_mm:g}     "
                    f"{result_input.rows_parallel_n} × {result_input.rows_perpendicular_m}"
                )
            )
        self.technical_source.configure(
            text="Quelle: " + ("; ".join(sources) if sources else "–")
        )

    def _update_status_block(self, result: StabduebelResult) -> None:
        validation = validate_oenorm(result.input, result)
        passed = validation.admissible
        color = self.GREEN if passed else self.RED
        background = "#E8F5EE" if passed else "#FBEAEC"
        data = result.input
        count = data.rows_parallel_n * data.rows_perpendicular_m
        utilization = result.governing_check.utilization
        self.ai_status_frame.configure(fg_color=background, border_color=color)
        self.ai_status_title.configure(
            text="✓ NACHWEIS ERFÜLLT" if passed else "✕ NACHWEIS NICHT ERFÜLLT",
            text_color=color,
        )
        self.ai_eta_label.configure(text=f"η = {utilization:.0%}", text_color=color)
        self.ai_status_details.configure(
            text=(
                f"Maximale Ausnutzung: {utilization:.0%}\n"
                f"Maßgebend: {result.governing_check.name}\n"
                f"Anschlussfall: {data.connection_case}\n"
                f"Scherfugen: {data.shear_planes_s}\n"
                f"Rechenmodell: {data.connection_model}\n"
                f"Stabdübel: {data.rows_parallel_n} × "
                f"{data.rows_perpendicular_m} = {count} · "
                f"Ø{data.dowel_diameter_d_mm:g} mm\n"
                f"Stahlbleche: {data.number_of_plates_ns} · "
                f"Dicke {data.plate_thickness_ts_mm:g} mm\n"
                f"Holzklasse: {data.timber_grade}\n"
                f"Nutzungsklasse: {data.service_class}\n"
                f"Lasteinwirkungsdauer: {data.load_duration_class}\n"
                f"kmod: {data.k_mod:g} · automatisch nach {KMOD_SOURCE}"
                + (
                    "\nValidierung: "
                    + "; ".join(check.name for check in validation.failures)
                    if validation.failures else ""
                )
                + (
                    "\nÖsterreichische Gesamtzulässigkeit: NEIN "
                    "(nur 2 Scherfugen)"
                    if data.number_of_plates_ns == 1 else ""
                )
            )
        )
        self.ai_utilization_bar.configure(progress_color=color)
        self.ai_utilization_bar.set(min(utilization, 1.0))

    def _clear_status_block(self) -> None:
        self.ai_status_frame.configure(fg_color="#EEF1F4", border_color=self.BORDER)
        self.ai_status_title.configure(text="NOCH KEIN NACHWEIS", text_color=self.MUTED)
        self.ai_eta_label.configure(text="η = –", text_color=self.MUTED)
        self.ai_status_details.configure(text="")
        self.ai_utilization_bar.configure(progress_color=self.MUTED)
        self.ai_utilization_bar.set(0)

    def _append_chat(self, sender: str, text: str) -> None:
        at_bottom = self.chat.yview()[1] >= 0.98
        self.chat.configure(state="normal")
        is_user = sender.lower() in {"sie", "du", "user"}
        heading = "DU" if is_user else "✦ KI"
        tag = "user_message" if is_user else "ai_message"
        self.chat.insert("end", f"{heading}\n{text}\n\n", tag)
        self.chat.configure(state="disabled")
        if at_bottom:
            self._scroll_chat_to_end()
        else:
            self.new_message_button.grid()

    def _clear_chat_placeholder(self, _event=None) -> None:
        if self.assistant_entry.get("1.0", "end-1c") == self._chat_placeholder:
            self.assistant_entry.delete("1.0", "end")
            self.assistant_entry.configure(text_color=self.TEXT)

    def _on_chat_enter(self, event) -> str:
        if event.state & 0x0001:
            return self._on_chat_shift_enter(event)
        self._send_to_assistant()
        return "break"

    def _on_chat_shift_enter(self, _event) -> str:
        self.assistant_entry.insert("insert", "\n")
        return "break"

    def _scroll_chat_to_end(self) -> None:
        self.chat.see("end")
        self.new_message_button.grid_remove()

    def _chat_selection_autoscroll(self, event) -> None:
        margin = 18
        height = self.chat.winfo_height()
        if event.y < margin:
            self.chat.yview_scroll(-1, "units")
        elif event.y > height - margin:
            self.chat.yview_scroll(1, "units")

    @staticmethod
    def _copy_chat_selection(event) -> str:
        event.widget.event_generate("<<Copy>>")
        return "break"

    def _load_manual_defaults(self) -> None:
        defaults = StabduebelInput()
        self.timber_grade.set(defaults.timber_grade)
        self.manual_service_class.set(str(defaults.service_class))
        self.manual_load_duration.set(defaults.load_duration_class)
        for key, entry in self.entries.items():
            entry.delete(0, "end")
            entry.insert(0, str(getattr(defaults, key)))
        self._update_manual_kmod()

    def _calculate_manual(self) -> None:
        try:
            values = asdict(StabduebelInput())
            for key, entry in self.entries.items():
                raw = entry.get().strip().replace(",", ".")
                if not raw:
                    raise ValueError(f"Das Feld '{key}' darf nicht leer sein.")
                kind = entry._value_kind  # type: ignore[attr-defined]
                values[key] = raw if kind == "text" else int(raw) if kind == "int" else float(raw)

            grade = self.timber_grade.get()
            material = self.materials.get(grade)
            values.update(
                timber_grade=grade,
                service_class=int(self.manual_service_class.get()),
                load_duration_class=self.manual_load_duration.get(),
                k_mod=self._update_manual_kmod(),
                gamma_m_timber=get_connection_gamma_m(),
                rho_k_kg_m3=material.value("rho_k"),
                ft_0_k_n_mm2=material.value("ft_0_k"),
                fv_k_n_mm2=material.value("fv_k"),
            )
            result = calculate_stabduebel(StabduebelInput(**values))
            self._update_manual_status_block(result)
            self._set_text(self.manual_result, self._detailed_result(result))
            self.manual_visualizer.update_input(result.input, result)
        except (ValueError, KeyError) as exc:
            messagebox.showerror("Ungültige Eingabe", str(exc))
        except Exception as exc:
            messagebox.showerror("Berechnungsfehler", str(exc))

    def _update_manual_status_block(self, result: StabduebelResult) -> None:
        validation = validate_oenorm(result.input, result)
        passed = validation.admissible
        color = self.GREEN if passed else self.RED
        background = "#E8F5EE" if passed else "#FBEAEC"
        data = result.input
        count = data.rows_parallel_n * data.rows_perpendicular_m
        utilization = result.governing_check.utilization

        self.manual_status_frame.configure(
            fg_color=background,
            border_color=color,
        )
        self.manual_status_title.configure(
            text="✓ NACHWEIS ERFÜLLT" if passed else "✕ NACHWEIS NICHT ERFÜLLT",
            text_color=color,
        )
        self.manual_eta_label.configure(text=f"η = {utilization:.0%}", text_color=color)
        self.manual_status_details.configure(
            text=(
                f"Maximale Ausnutzung: {utilization:.0%}\n"
                f"Maßgebend: {result.governing_check.name}\n"
                f"Anschlussfall: {data.connection_case}\n"
                f"Scherfugen: {data.shear_planes_s}\n"
                f"Rechenmodell: {data.connection_model}\n"
                f"Holzklasse: {data.timber_grade}\n"
                f"Nutzungsklasse: {data.service_class}\n"
                f"Lasteinwirkungsdauer: {data.load_duration_class}\n"
                f"kmod: {data.k_mod:g} · automatisch nach {KMOD_SOURCE}\n"
                f"Querschnitt: {data.width_b_mm:g} × {data.height_h_mm:g} mm\n"
                f"Stabdübel: {data.rows_parallel_n} × "
                f"{data.rows_perpendicular_m} = {count} · "
                f"Ø{data.dowel_diameter_d_mm:g} mm\n"
                f"Stahlbleche: {data.number_of_plates_ns} · "
                f"Dicke {data.plate_thickness_ts_mm:g} mm"
                + (
                    "\nValidierung: "
                    + "; ".join(check.name for check in validation.failures)
                    if validation.failures else ""
                )
                + (
                    "\nÖsterreichische Gesamtzulässigkeit: NEIN "
                    "(nur 2 Scherfugen)"
                    if data.number_of_plates_ns == 1 else ""
                )
            ),
            text_color=self.TEXT,
        )
        self.manual_utilization_bar.configure(progress_color=color)
        self.manual_utilization_bar.set(min(utilization, 1.0))

    @staticmethod
    def _detailed_result(result: StabduebelResult) -> str:
        validation = validate_oenorm(result.input, result)
        lines = [
            f"Anschlussfall: {result.input.connection_case}",
            f"Scherfugen: {result.input.shear_planes_s}",
            f"Rechenmodell: {result.input.connection_model}",
            f"Holzklasse: {result.input.timber_grade}",
            f"Nutzungsklasse: {result.input.service_class}",
            f"Lasteinwirkungsdauer: {result.input.load_duration_class}",
            f"kmod: {result.input.k_mod:g}",
            f"Quelle kmod: automatisch nach {KMOD_SOURCE}",
            f"Last: {result.input.force_ed_kn:.2f} kN",
            f"Anordnung: {result.input.rows_parallel_n} × "
            f"{result.input.rows_perpendicular_m} = "
            f"{result.input.rows_parallel_n * result.input.rows_perpendicular_m} "
            "Stabdübel",
            f"Stahlbleche: {result.input.number_of_plates_ns} × "
            f"{result.input.plate_thickness_ts_mm:g} mm",
            "",
        ]
        for check in result.checks:
            status = "OK" if check.passed else "NICHT ERFÜLLT"
            lines.append(
                f"{check.name}\n  Rd = {check.resistance_kn:.2f} kN | "
                f"η = {check.utilization:.2f} | {status}\n"
            )
        lines.extend(
            [
                f"Maßgebend: {result.governing_check.name}",
                f"Maximale Ausnutzung: {result.governing_check.utilization:.2f}",
                "TRAGFÄHIGKEITSNACHWEISE: "
                + ("ERFÜLLT" if result.passed else "NICHT ERFÜLLT"),
                "",
                "TECHNISCHE VALIDIERUNG · Normprofil ÖNORM",
            ]
        )
        for check in validation.checks:
            symbol = (
                "✓" if check.status is ValidationStatus.PASSED
                else "✕" if check.status is ValidationStatus.FAILED
                else "!"
            )
            lines.append(
                f"{symbol} {check.name}: {check.status.value}\n"
                f"  {check.message}\n  Quelle: {check.source}"
            )
        lines.append(
            "TECHNISCHES GESAMTERGEBNIS: "
            + ("ZULÄSSIG UND ERFÜLLT" if validation.admissible else "NICHT ZULÄSSIG")
        )
        return "\n".join(lines)

    @staticmethod
    def _set_text(widget: ctk.CTkTextbox, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text)
        widget.configure(state="disabled")


def main() -> None:
    app = StabduebelApp()
    splash = SplashScreen(app)

    def finish_startup() -> None:
        splash.progress.stop()
        splash.destroy()
        app.deiconify()
        app.lift()
        app.focus_force()

    app.after(3000, finish_startup)
    app.mainloop()


if __name__ == "__main__":
    main()
