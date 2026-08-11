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
from infopol.materials import TimberMaterialRepository


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
        ("side_thickness_t1_mm", "Seitenholz t1 [mm]", "float"),
        ("middle_thickness_t2_mm", "Mittelholz t2 [mm]", "float"),
        ("number_of_plates_ns", "Anzahl Bleche", "int"),
        ("plate_thickness_ts_mm", "Blechdicke ts [mm]", "float"),
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
        ("k_mod", "kmod [-]", "float"),
        ("gamma_m_timber", "γM Holz [-]", "float"),
        ("kt_e_side", "kt,e Seitenholz [-]", "float"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.withdraw()
        self.title("KI-gestützte Stabdübelbemessung – V1")
        self.geometry("1240x820")
        self.minsize(1040, 700)
        self.configure(fg_color=self.BG)

        self.materials = TimberMaterialRepository()
        self.assistant = StabduebelAssistant()
        self.entries: dict[str, ctk.CTkEntry] = {}
        self.timber_grade = tk.StringVar(value=StabduebelInput().timber_grade)

        self._build_header()
        self._build_tabs()
        self._load_manual_defaults()

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
            text="KI-gestützte Stabdübelbemessung",
            font=ctk.CTkFont(size=25, weight="bold"),
            text_color=self.TEXT,
        ).pack(anchor="w", pady=(18, 2))
        ctk.CTkLabel(
            heading,
            text="V1-Prototyp · KI für Sprache, Python für sämtliche Nachweise",
            font=ctk.CTkFont(size=13),
            text_color=self.MUTED,
        ).pack(anchor="w")

    def _build_tabs(self) -> None:
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=self.BG,
            segmented_button_selected_color=self.RED,
            segmented_button_selected_hover_color=self.RED_DARK,
        )
        self.tabs.pack(fill="both", expand=True, padx=26, pady=18)
        assistant_tab = self.tabs.add("KI-Assistent")
        manual_tab = self.tabs.add("Manuelle Eingabe")
        self._build_assistant_tab(assistant_tab)
        self._build_manual_tab(manual_tab)

    def _build_assistant_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=3)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)

        chat_card = ctk.CTkFrame(tab, fg_color=self.CARD, corner_radius=14)
        chat_card.grid(row=0, column=0, sticky="nsew", padx=(8, 10), pady=10)
        chat_card.grid_columnconfigure(0, weight=1)
        chat_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            chat_card,
            text="Entwurfsdialog",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 8))

        self.chat = ctk.CTkTextbox(
            chat_card,
            wrap="word",
            font=ctk.CTkFont(size=13),
            fg_color="#F8F9FA",
            border_width=1,
            border_color=self.BORDER,
        )
        self.chat.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 12))
        self.chat.insert(
            "end",
            "Assistent:\nBeschreiben Sie Last, Holzklasse und Entwurfsziel. "
            "Zum Beispiel: ‚Bemesse einen Stabdübelanschluss für 140 kN mit "
            "GL24h und möglichst wenigen Stabdübeln.‘\n\n",
        )
        self.chat.configure(state="disabled")

        input_row = ctk.CTkFrame(chat_card, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 18))
        input_row.grid_columnconfigure(0, weight=1)
        self.assistant_entry = ctk.CTkEntry(
            input_row,
            height=42,
            placeholder_text="Anforderung oder Folgeprompt eingeben …",
            border_color=self.BORDER,
        )
        self.assistant_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.assistant_entry.bind("<Return>", lambda _event: self._send_to_assistant())
        self.send_button = ctk.CTkButton(
            input_row,
            text="Senden",
            width=100,
            height=42,
            fg_color=self.RED,
            hover_color=self.RED_DARK,
            command=self._send_to_assistant,
        )
        self.send_button.grid(row=0, column=1)

        result_card = ctk.CTkFrame(tab, fg_color=self.CARD, corner_radius=14)
        result_card.grid(row=0, column=1, sticky="nsew", padx=(10, 8), pady=10)
        result_card.grid_columnconfigure(0, weight=1)
        result_card.grid_rowconfigure(6, weight=1)
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

        ctk.CTkLabel(
            result_card,
            text="Erkannte Vorgaben",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=2, column=0, sticky="w", padx=20, pady=(14, 4))
        self.recognized_values = ctk.CTkLabel(
            result_card,
            text="Noch keine Vorgaben erkannt.",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=self.MUTED,
        )
        self.recognized_values.grid(row=3, column=0, sticky="ew", padx=20)

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
        self.ai_status_details = ctk.CTkLabel(
            self.ai_status_frame,
            text="",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT,
        )
        self.ai_status_details.grid(row=1, column=0, sticky="ew", padx=16)
        self.ai_utilization_bar = ctk.CTkProgressBar(
            self.ai_status_frame,
            height=12,
            progress_color=self.MUTED,
            fg_color="#D8DDE3",
        )
        self.ai_utilization_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(9, 14))
        self.ai_utilization_bar.set(0)

        ctk.CTkLabel(
            result_card,
            text="Technisches Ergebnis",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=5, column=0, sticky="w", padx=20, pady=(5, 3))
        self.ai_result = ctk.CTkTextbox(
            result_card,
            wrap="word",
            font=ctk.CTkFont(family="Courier", size=12),
            fg_color="#F8F9FA",
            border_width=1,
            border_color=self.BORDER,
        )
        self.ai_result.grid(row=6, column=0, sticky="nsew", padx=20, pady=(0, 8))
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
        ctk.CTkButton(
            result_card,
            text="Dialog zurücksetzen",
            fg_color="#E9ECEF",
            hover_color="#DDE1E5",
            text_color=self.TEXT,
            command=self._reset_assistant,
        ).grid(row=9, column=0, sticky="ew", padx=20, pady=(0, 18))

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
        for row, (key, label, kind) in enumerate(self.MANUAL_FIELDS, start=1):
            ctk.CTkLabel(form, text=label, text_color=self.TEXT, anchor="w").grid(
                row=row, column=0, sticky="w", padx=12, pady=5
            )
            entry = ctk.CTkEntry(form, width=170, border_color=self.BORDER)
            entry.grid(row=row, column=1, sticky="e", padx=12, pady=5)
            entry._value_kind = kind  # type: ignore[attr-defined]
            self.entries[key] = entry

        button_row = len(self.MANUAL_FIELDS) + 1
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

        result = ctk.CTkFrame(tab, fg_color=self.CARD, corner_radius=14)
        result.grid(row=0, column=1, sticky="nsew", padx=(10, 8), pady=10)
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
        self.manual_status_details = ctk.CTkLabel(
            self.manual_status_frame,
            text="Nach der Berechnung erscheint hier die Zusammenfassung.",
            justify="left",
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color=self.MUTED,
        )
        self.manual_status_details.grid(
            row=1, column=0, sticky="ew", padx=18
        )
        self.manual_utilization_bar = ctk.CTkProgressBar(
            self.manual_status_frame,
            height=13,
            progress_color=self.MUTED,
            fg_color="#D8DDE3",
        )
        self.manual_utilization_bar.grid(
            row=2, column=0, sticky="ew", padx=18, pady=(11, 17)
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
        ).grid(row=0, column=1, sticky="e", padx=12, pady=5)

    def _send_to_assistant(self) -> None:
        text = self.assistant_entry.get().strip()
        if not text:
            return
        self.assistant_entry.delete(0, "end")
        self._append_chat("Sie", text)
        self.send_button.configure(state="disabled", text="Berechnet …")
        self.ai_mode_label.configure(text="Anfrage wird verarbeitet …")
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
            "Lokale Demo-Erkennung + deterministischer Rechenkern"
        )
        self.ai_mode_label.configure(text=mode)
        self.recognized_values.configure(
            text=reply.recognized_parameters or "Noch keine Vorgaben erkannt."
        )
        self._set_text(self.ai_interpretation, reply.interpretation)
        if reply.result:
            self._set_text(self.ai_result, self._detailed_result(reply.result))
            self._update_status_block(reply.result)
        else:
            self._clear_status_block()
        self.send_button.configure(state="normal", text="Senden")

    def _show_assistant_error(self, error: str) -> None:
        self._append_chat("Fehler", error)
        self.ai_mode_label.configure(text="Fehler")
        self.send_button.configure(state="normal", text="Senden")

    def _reset_assistant(self) -> None:
        self.assistant.reset()
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.insert("end", "Assistent:\nNeuer Entwurfsdialog gestartet.\n\n")
        self.chat.configure(state="disabled")
        self._set_text(self.ai_result, "")
        self._set_text(self.ai_interpretation, "")
        self.recognized_values.configure(text="Noch keine Vorgaben erkannt.")
        self._clear_status_block()
        self.ai_mode_label.configure(text="Bereit")

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
        self.ai_status_details.configure(
            text=(
                f"Maximale Ausnutzung: {utilization:.0%}\n"
                f"Maßgebend: {result.governing_check.name}\n"
                f"Stabdübel: {data.rows_parallel_n} × "
                f"{data.rows_perpendicular_m} = {count} · "
                f"Ø{data.dowel_diameter_d_mm:g} mm\n"
                f"Stahlbleche: {data.number_of_plates_ns} · "
                f"Dicke {data.plate_thickness_ts_mm:g} mm\n"
                f"Holzklasse: {data.timber_grade}"
                + (
                    "\nValidierung: "
                    + "; ".join(check.name for check in validation.failures)
                    if validation.failures else ""
                )
            )
        )
        self.ai_utilization_bar.configure(progress_color=color)
        self.ai_utilization_bar.set(min(utilization, 1.0))

    def _clear_status_block(self) -> None:
        self.ai_status_frame.configure(fg_color="#EEF1F4", border_color=self.BORDER)
        self.ai_status_title.configure(text="NOCH KEIN NACHWEIS", text_color=self.MUTED)
        self.ai_status_details.configure(text="")
        self.ai_utilization_bar.configure(progress_color=self.MUTED)
        self.ai_utilization_bar.set(0)

    def _append_chat(self, sender: str, text: str) -> None:
        self.chat.configure(state="normal")
        self.chat.insert("end", f"{sender}:\n{text}\n\n")
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def _load_manual_defaults(self) -> None:
        defaults = StabduebelInput()
        self.timber_grade.set(defaults.timber_grade)
        for key, entry in self.entries.items():
            entry.delete(0, "end")
            entry.insert(0, str(getattr(defaults, key)))

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
                rho_k_kg_m3=material.value("rho_k"),
                ft_0_k_n_mm2=material.value("ft_0_k"),
                fv_k_n_mm2=material.value("fv_k"),
            )
            result = calculate_stabduebel(StabduebelInput(**values))
            self._update_manual_status_block(result)
            self._set_text(self.manual_result, self._detailed_result(result))
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
        self.manual_status_details.configure(
            text=(
                f"Maximale Ausnutzung: {utilization:.0%}\n"
                f"Maßgebend: {result.governing_check.name}\n"
                f"Holzklasse: {data.timber_grade}\n"
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
            ),
            text_color=self.TEXT,
        )
        self.manual_utilization_bar.configure(progress_color=color)
        self.manual_utilization_bar.set(min(utilization, 1.0))

    @staticmethod
    def _detailed_result(result: StabduebelResult) -> str:
        validation = validate_oenorm(result.input, result)
        lines = [
            f"Holzklasse: {result.input.timber_grade}",
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

    app.after(1600, finish_startup)
    app.mainloop()


if __name__ == "__main__":
    main()
