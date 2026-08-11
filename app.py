from __future__ import annotations

"""Professionelle Desktop-GUI für das KI-gestützte Bemessungstool.

Projektstruktur:
    Vortrag Klagenfurt/
    ├── app.py
    ├── holzbau_logo_farb.png
    └── calculations/
        ├── __init__.py
        └── stabduebel.py

Start:
    pip install customtkinter pillow
    python app.py
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk
from PIL import Image

from calculations.stabduebel import (
    StabduebelInput,
    StabduebelResult,
    calculate_stabduebel,
)

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


class StabduebelApp(ctk.CTk):
    RED = "#B20D30"
    RED_DARK = "#890923"
    RED_SOFT = "#F7E8EC"
    BG = "#F3F4F6"
    CARD = "#FFFFFF"
    TEXT = "#20242A"
    MUTED = "#6B7280"
    BORDER = "#E4E7EB"
    GREEN = "#228B57"
    ORANGE = "#D68A00"
    BLUE_GREY = "#263746"

    def __init__(self) -> None:
        super().__init__()

        self.title("KI-gestütztes Bemessungstool für Holzverbindungen")
        self.geometry("1540x940")
        self.minsize(1240, 780)
        self.configure(fg_color=self.BG)

        self.entries: dict[str, ctk.CTkEntry] = {}
        self.pages: dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.current_page = ""
        self.last_result: StabduebelResult | None = None
        self.logo_image: ctk.CTkImage | None = None

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._load_logo()
        self._build_sidebar()
        self._build_page_container()
        self._build_dashboard_page()
        self._build_stabduebel_page()
        self._build_placeholder_pages()
        self._load_default_values()
        self.show_page("dashboard")

    # ------------------------------------------------------------------
    # Grundlayout
    # ------------------------------------------------------------------

    def _load_logo(self) -> None:
        candidates = [
            Path(__file__).with_name("Logo.png"),
            Path(__file__).with_name("logo.png"),
        ]
        for path in candidates:
            if path.exists():
                image = Image.open(path)
                self.logo_image = ctk.CTkImage(light_image=image, dark_image=image, size=(196, 62))
                return

    def _build_sidebar(self) -> None:
        self.sidebar = ctk.CTkFrame(
            self,
            width=286,
            corner_radius=0,
            fg_color=self.BLUE_GREY,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=22, pady=(25, 18))

        if self.logo_image:
            ctk.CTkLabel(brand, text="", image=self.logo_image).pack(anchor="w")
        else:
            ctk.CTkLabel(
                brand,
                text="HOLZBAU\nINSTITUT",
                font=ctk.CTkFont(size=23, weight="bold"),
                text_color="white",
                justify="left",
            ).pack(anchor="w")

        ctk.CTkLabel(
            brand,
            text="KI-BEMESSUNGSTOOL",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#DCE5EC",
        ).pack(anchor="w", pady=(8, 0))

        self._nav_button("dashboard", "⌂  Dashboard")
        self._nav_separator()
        self._nav_heading("VERBINDUNGEN")
        self._nav_button("stabduebel", "●  Stabdübel")
        self._nav_button("schraegschrauben", "↗  Schrägschrauben")
        self._nav_button("gewindestangen", "│  Eingeklebte Gewindestangen")
        self._nav_separator()
        self._nav_heading("VERGLEICH")
        self._nav_button("vergleich", "≋  Variantenvergleich")
        self._nav_separator()
        self._nav_heading("DOKUMENTATION")
        self._nav_button("berichte", "▤  Berichte")
        self._nav_separator()
        self._nav_button("einstellungen", "⚙  Einstellungen")

        ctk.CTkLabel(
            self.sidebar,
            text="Masterarbeit · Prototyp 2026\nInstitut für Holzbau und Holztechnologie",
            font=ctk.CTkFont(size=11),
            text_color="#AFC0CC",
            justify="left",
        ).pack(side="bottom", anchor="w", padx=22, pady=22)

    def _nav_heading(self, text: str) -> None:
        ctk.CTkLabel(
            self.sidebar,
            text=text,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#91A6B6",
        ).pack(anchor="w", padx=23, pady=(7, 5))

    def _nav_separator(self) -> None:
        ctk.CTkFrame(self.sidebar, height=1, fg_color="#415260").pack(
            fill="x", padx=20, pady=10
        )

    def _nav_button(self, page: str, text: str) -> None:
        button = ctk.CTkButton(
            self.sidebar,
            text=text,
            height=43,
            corner_radius=9,
            anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="transparent",
            hover_color="#354A59",
            text_color="#F3F6F8",
            command=lambda name=page: self.show_page(name),
        )
        button.pack(fill="x", padx=13, pady=3)
        self.nav_buttons[page] = button

    def _build_page_container(self) -> None:
        self.page_container = ctk.CTkFrame(self, corner_radius=0, fg_color=self.BG)
        self.page_container.grid(row=0, column=1, sticky="nsew")
        self.page_container.grid_columnconfigure(0, weight=1)
        self.page_container.grid_rowconfigure(0, weight=1)

    def _new_page(self, name: str) -> ctk.CTkFrame:
        page = ctk.CTkFrame(self.page_container, corner_radius=0, fg_color=self.BG)
        page.grid(row=0, column=0, sticky="nsew")
        self.pages[name] = page
        return page

    def show_page(self, name: str) -> None:
        if name not in self.pages:
            return
        self.pages[name].tkraise()
        self.current_page = name
        for key, button in self.nav_buttons.items():
            selected = key == name
            button.configure(
                fg_color=self.RED if selected else "transparent",
                hover_color=self.RED_DARK if selected else "#354A59",
            )

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def _build_dashboard_page(self) -> None:
        page = self._new_page("dashboard")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        header = self._page_header(
            page,
            "KI-gestütztes Bemessungstool für Holzverbindungen",
            "Automatisierte Nachweise, Variantenvergleich und Berichtserstellung",
        )
        header.grid(row=0, column=0, sticky="ew")

        content = ctk.CTkScrollableFrame(page, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=34, pady=(0, 26))
        content.grid_columnconfigure((0, 1), weight=1)

        overview = ctk.CTkFrame(content, fg_color=self.CARD, corner_radius=14)
        overview.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(5, 22))
        overview.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            overview,
            text="Projektübersicht",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(21, 5))
        ctk.CTkLabel(
            overview,
            text=(
                "Wählen Sie eine Verbindung, erfassen Sie Geometrie, Materialien und Lasten "
                "und lassen Sie die maßgebenden Nachweise automatisch auswerten."
            ),
            font=ctk.CTkFont(size=14),
            text_color=self.MUTED,
            wraplength=900,
            justify="left",
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 22))

        cards = [
            ("＋", "Neue Berechnung", "Stabdübel-Nachweis starten", "stabduebel", self.RED),
            ("▣", "Projekte öffnen", "Gespeicherte Projekte laden", "berichte", "#4B6578"),
            ("▤", "Letzte Berechnungen", "Zuletzt bearbeitete Nachweise", "berichte", "#7A526B"),
            ("⚙", "Einstellungen", "Darstellung und Projektoptionen", "einstellungen", "#4E6655"),
        ]
        for index, card in enumerate(cards):
            row, column = divmod(index, 2)
            self._dashboard_card(content, row + 1, column, *card)

        status = ctk.CTkFrame(content, fg_color=self.CARD, corner_radius=14)
        status.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(22, 10))
        status.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            status,
            text="PHASE 1",
            width=90,
            height=32,
            corner_radius=8,
            fg_color=self.RED_SOFT,
            text_color=self.RED,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=0, padx=22, pady=22)
        ctk.CTkLabel(
            status,
            text="Stabdübel-Berechnung vollständig integriert",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(
            status,
            text="Schrägschrauben, Gewindestangen und Variantenvergleich folgen als nächste Module.",
            font=ctk.CTkFont(size=13),
            text_color=self.MUTED,
        ).grid(row=1, column=1, sticky="w", pady=(0, 18))

    def _dashboard_card(
        self,
        parent: ctk.CTkFrame,
        row: int,
        column: int,
        icon: str,
        title: str,
        subtitle: str,
        page: str,
        accent: str,
    ) -> None:
        card = ctk.CTkFrame(parent, fg_color=self.CARD, corner_radius=14)
        card.grid(row=row, column=column, sticky="nsew", padx=(0, 11) if column == 0 else (11, 0), pady=10)
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text=icon,
            width=58,
            height=58,
            corner_radius=12,
            fg_color=accent,
            text_color="white",
            font=ctk.CTkFont(size=25, weight="bold"),
        ).grid(row=0, column=0, rowspan=2, padx=20, pady=24)
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=1, sticky="sw", pady=(24, 3))
        ctk.CTkLabel(
            card,
            text=subtitle,
            font=ctk.CTkFont(size=13),
            text_color=self.MUTED,
        ).grid(row=1, column=1, sticky="nw")
        ctk.CTkButton(
            card,
            text="Öffnen  →",
            width=96,
            height=36,
            fg_color="transparent",
            hover_color=self.RED_SOFT,
            text_color=self.RED,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=lambda: self.show_page(page),
        ).grid(row=0, column=2, rowspan=2, padx=18)

    # ------------------------------------------------------------------
    # Stabdübel-Seite
    # ------------------------------------------------------------------

    def _build_stabduebel_page(self) -> None:
        page = self._new_page("stabduebel")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)

        header = self._page_header(
            page,
            "Stabdübel-Zugstoß",
            "Parametrisierbarer Nachweis eines vier-schnittigen Anschlusses",
            action_text="PDF-Bericht",
            action=self._pdf_placeholder,
        )
        header.grid(row=0, column=0, sticky="ew")

        body = ctk.CTkFrame(page, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 24))
        body.grid_columnconfigure(0, weight=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.input_panel = ctk.CTkScrollableFrame(
            body,
            width=400,
            corner_radius=14,
            fg_color=self.CARD,
            label_text="① Eingabedaten",
            label_font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.input_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        right = ctk.CTkScrollableFrame(body, fg_color="transparent", corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        right.grid_columnconfigure(0, weight=1)

        self.sketch_card = ctk.CTkFrame(right, fg_color=self.CARD, corner_radius=14)
        self.sketch_card.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        self.sketch_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self.sketch_card,
            text="② Verbindungsskizze",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(18, 5))
        ctk.CTkLabel(
            self.sketch_card,
            text="Schematische Darstellung · automatische Aktualisierung nach Berechnung",
            font=ctk.CTkFont(size=12),
            text_color=self.MUTED,
        ).grid(row=1, column=0, sticky="w", padx=22)
        self.sketch_canvas = tk.Canvas(
            self.sketch_card,
            height=245,
            bg=self.CARD,
            highlightthickness=0,
        )
        self.sketch_canvas.grid(row=2, column=0, sticky="ew", padx=20, pady=(8, 20))
        self.sketch_canvas.bind("<Configure>", lambda _event: self._draw_connection_sketch())

        self.result_panel = ctk.CTkFrame(right, fg_color="transparent")
        self.result_panel.grid(row=1, column=0, sticky="ew")
        self.result_panel.grid_columnconfigure(0, weight=1)

        self._build_input_fields()
        self._build_result_placeholder()

    def _build_input_fields(self) -> None:
        self._section("Projekt und Lasten")
        self._entry("project_name", "Projektname", is_text=True)
        self._entry("force_ed_kn", "Bemessungslast Ft,d [kN]")

        self._section("Holz")
        self._entry("width_b_mm", "Breite b [mm]")
        self._entry("height_h_mm", "Höhe h [mm]")
        self._entry("side_thickness_t1_mm", "Seitenholz t1 [mm]")
        self._entry("middle_thickness_t2_mm", "Mittelholz t2 [mm]")
        self._entry("rho_k_kg_m3", "Rohdichte ρk [kg/m³]")
        self._entry("ft_0_k_n_mm2", "Zugfestigkeit ft,0,k [N/mm²]")
        self._entry("fv_k_n_mm2", "Schubfestigkeit fv,k [N/mm²]")

        self._section("Stahl")
        self._entry("number_of_plates_ns", "Anzahl Bleche", integer=True)
        self._entry("plate_thickness_ts_mm", "Blechdicke ts [mm]")
        self._entry("e1_mm", "Randabstand e1 [mm]")
        self._entry("e2_mm", "Randabstand e2 [mm]")

        self._section("Verbindungsmittel")
        self._entry("dowel_diameter_d_mm", "Dübeldurchmesser d [mm]")
        self._entry("dowel_length_l_mm", "Dübellänge l [mm]")
        self._entry("hole_diameter_d0_mm", "Lochdurchmesser d0 [mm]")
        self._entry("rows_parallel_n", "Reihen parallel n", integer=True)
        self._entry("rows_perpendicular_m", "Reihen quer m", integer=True)

        self._section("Abstände")
        self._entry("a1_mm", "a1 [mm]")
        self._entry("a2_mm", "a2 [mm]")
        self._entry("a3_t_mm", "a3,t [mm]")
        self._entry("a4_c_mm", "a4,c [mm]")

        self._section("Sicherheitsbeiwerte")
        self._entry("k_mod", "kmod [-]")
        self._entry("gamma_m_timber", "γM Holz [-]")
        self._entry("kt_e_side", "kt,e Seitenholz [-]")

        buttons = ctk.CTkFrame(self.input_panel, fg_color="transparent")
        buttons.pack(fill="x", padx=10, pady=(20, 22))
        ctk.CTkButton(
            buttons,
            text="Nachweis berechnen",
            height=48,
            corner_radius=9,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=self.RED,
            hover_color=self.RED_DARK,
            command=self.calculate,
        ).pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            buttons,
            text="Standardwerte laden",
            height=38,
            fg_color="#E9ECEF",
            hover_color="#DDE1E5",
            text_color=self.TEXT,
            command=self._load_default_values,
        ).pack(fill="x")

    def _section(self, title: str) -> None:
        ctk.CTkLabel(
            self.input_panel,
            text=title.upper(),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.RED,
            anchor="w",
        ).pack(fill="x", padx=10, pady=(18, 7))

    def _entry(
        self,
        key: str,
        label: str,
        *,
        integer: bool = False,
        is_text: bool = False,
    ) -> None:
        frame = ctk.CTkFrame(self.input_panel, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=4)
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=self.TEXT,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 10))

        validate_command: tuple[str, str] | None = None
        if not is_text:
            validator: Callable[[str], bool]
            validator = self._validate_integer if integer else self._validate_float
            validate_command = (self.register(validator), "%P")

        entry = ctk.CTkEntry(
            frame,
            width=130,
            height=34,
            justify="right" if not is_text else "left",
            border_color=self.BORDER,
            validate="key" if validate_command else "none",
            validatecommand=validate_command,
        )
        entry.grid(row=0, column=1, sticky="e")
        self.entries[key] = entry

    # ------------------------------------------------------------------
    # Ergebnisse
    # ------------------------------------------------------------------

    def _build_result_placeholder(self) -> None:
        for widget in self.result_panel.winfo_children():
            widget.destroy()
        placeholder = ctk.CTkFrame(self.result_panel, fg_color=self.CARD, corner_radius=14)
        placeholder.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            placeholder,
            text="③ Ergebnisse",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.TEXT,
        ).pack(anchor="w", padx=22, pady=(19, 8))
        ctk.CTkLabel(
            placeholder,
            text="Nach dem Start der Berechnung werden hier alle Nachweise übersichtlich dargestellt.",
            font=ctk.CTkFont(size=13),
            text_color=self.MUTED,
            wraplength=650,
            justify="left",
        ).pack(anchor="w", padx=22, pady=(0, 22))
        self._draw_connection_sketch()

    def calculate(self) -> None:
        try:
            data = StabduebelInput(
                project_name=self._text("project_name"),
                force_ed_kn=self._float("force_ed_kn"),
                width_b_mm=self._float("width_b_mm"),
                height_h_mm=self._float("height_h_mm"),
                side_thickness_t1_mm=self._float("side_thickness_t1_mm"),
                middle_thickness_t2_mm=self._float("middle_thickness_t2_mm"),
                dowel_diameter_d_mm=self._float("dowel_diameter_d_mm"),
                dowel_length_l_mm=self._float("dowel_length_l_mm"),
                hole_diameter_d0_mm=self._float("hole_diameter_d0_mm"),
                rows_parallel_n=self._int("rows_parallel_n"),
                rows_perpendicular_m=self._int("rows_perpendicular_m"),
                a1_mm=self._float("a1_mm"),
                a2_mm=self._float("a2_mm"),
                a3_t_mm=self._float("a3_t_mm"),
                a4_c_mm=self._float("a4_c_mm"),
                number_of_plates_ns=self._int("number_of_plates_ns"),
                plate_thickness_ts_mm=self._float("plate_thickness_ts_mm"),
                e1_mm=self._float("e1_mm"),
                e2_mm=self._float("e2_mm"),
                rho_k_kg_m3=self._float("rho_k_kg_m3"),
                ft_0_k_n_mm2=self._float("ft_0_k_n_mm2"),
                fv_k_n_mm2=self._float("fv_k_n_mm2"),
                k_mod=self._float("k_mod"),
                gamma_m_timber=self._float("gamma_m_timber"),
                kt_e_side=self._float("kt_e_side"),
            )
            self.last_result = calculate_stabduebel(data)
            self._display_results(self.last_result)
            self._draw_connection_sketch()
        except ValueError as exc:
            messagebox.showerror("Ungültige Eingabe", str(exc))
        except Exception as exc:
            messagebox.showerror(
                "Berechnungsfehler",
                f"Die Berechnung konnte nicht ausgeführt werden:\n\n{exc}",
            )

    def _display_results(self, result: StabduebelResult) -> None:
        for widget in self.result_panel.winfo_children():
            widget.destroy()

        heading = ctk.CTkFrame(self.result_panel, fg_color="transparent")
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(
            heading,
            text="③ Ergebnisse",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.TEXT,
        ).pack(anchor="w")

        cards = ctk.CTkFrame(self.result_panel, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew")
        cards.grid_columnconfigure((0, 1), weight=1)

        checks = list(result.checks)
        preferred = ["Seitenholz", "Mittelholz", "Johansen", "Blockversagen"]
        selected = []
        for label in preferred:
            match = next((check for check in checks if label.lower() in check.name.lower()), None)
            if match and match not in selected:
                selected.append(match)
        for check in checks:
            if len(selected) >= 4:
                break
            if check not in selected:
                selected.append(check)

        for index, check in enumerate(selected[:4]):
            row, column = divmod(index, 2)
            self._result_summary_card(cards, row, column, check, check.name == result.governing_check.name)

        details = ctk.CTkFrame(self.result_panel, fg_color=self.CARD, corner_radius=14)
        details.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        details.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            details,
            text="Alle Nachweise",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=20, pady=(17, 10))
        for row, check in enumerate(checks, start=1):
            color = self.GREEN if check.passed else self.RED
            ctk.CTkLabel(details, text=check.name, text_color=self.TEXT).grid(
                row=row, column=0, sticky="w", padx=20, pady=5
            )
            ctk.CTkLabel(details, text=f"Rd = {check.resistance_kn:.2f} kN", text_color=self.MUTED).grid(
                row=row, column=1, sticky="e", padx=15
            )
            ctk.CTkLabel(
                details,
                text=f"η = {check.utilization:.2f}",
                text_color=color,
                font=ctk.CTkFont(weight="bold"),
            ).grid(row=row, column=2, sticky="e", padx=20)
        ctk.CTkLabel(details, text="").grid(row=len(checks) + 1, column=0, pady=5)

        self._build_final_summary(result, row=3)

    def _result_summary_card(self, parent, row, column, check, governing: bool) -> None:
        color = self.GREEN if check.passed else self.RED
        card = ctk.CTkFrame(
            parent,
            fg_color=self.CARD,
            corner_radius=14,
            border_width=2 if governing else 1,
            border_color=self.ORANGE if governing else self.BORDER,
        )
        card.grid(
            row=row,
            column=column,
            sticky="nsew",
            padx=(0, 9) if column == 0 else (9, 0),
            pady=9,
        )
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            card,
            text=check.name,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 4))
        if governing:
            ctk.CTkLabel(
                card,
                text="MAẞGEBEND",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=self.ORANGE,
            ).grid(row=0, column=1, sticky="e", padx=18)
        ctk.CTkLabel(
            card,
            text=f"{check.resistance_kn:.2f} kN",
            font=ctk.CTkFont(size=23, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(5, 2))
        ctk.CTkLabel(
            card,
            text="Rd",
            font=ctk.CTkFont(size=11),
            text_color=self.MUTED,
        ).grid(row=2, column=0, sticky="w", padx=18)
        ctk.CTkLabel(
            card,
            text=f"η = {check.utilization:.2f}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=color,
        ).grid(row=1, column=1, rowspan=2, sticky="e", padx=18)
        ctk.CTkProgressBar(card, progress_color=color, fg_color="#E9ECEF").grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=18, pady=(13, 18)
        )
        progress = card.winfo_children()[-1]
        progress.set(min(max(check.utilization, 0.0), 1.0))

    def _build_final_summary(self, result: StabduebelResult, row: int) -> None:
        color = self.GREEN if result.passed else self.RED
        summary = ctk.CTkFrame(
            self.result_panel,
            fg_color=color,
            corner_radius=14,
        )
        summary.grid(row=row, column=0, sticky="ew", pady=(18, 5))
        summary.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            summary,
            text="④ Zusammenfassung",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#EAF7EF",
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(17, 4))
        ctk.CTkLabel(
            summary,
            text="✓ Nachweis erfüllt" if result.passed else "✕ Nachweis nicht erfüllt",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white",
        ).grid(row=1, column=0, sticky="w", padx=22)
        ctk.CTkLabel(
            summary,
            text=f"Maßgebend: {result.governing_check.name}",
            font=ctk.CTkFont(size=14),
            text_color="white",
        ).grid(row=2, column=0, sticky="w", padx=22, pady=(8, 19))
        ctk.CTkLabel(
            summary,
            text=f"η = {result.governing_check.utilization:.2f}",
            font=ctk.CTkFont(size=25, weight="bold"),
            text_color="white",
        ).grid(row=0, column=1, rowspan=3, sticky="e", padx=25)

    # ------------------------------------------------------------------
    # Skizze
    # ------------------------------------------------------------------

    def _draw_connection_sketch(self) -> None:
        if not hasattr(self, "sketch_canvas"):
            return
        canvas = self.sketch_canvas
        canvas.delete("all")
        width = max(canvas.winfo_width(), 620)
        height = max(canvas.winfo_height(), 230)
        cx = width / 2
        top = 35
        layer_h = 31
        layer_w = min(width - 120, 690)
        x1, x2 = cx - layer_w / 2, cx + layer_w / 2

        timber = "#D9A35F"
        timber_dark = "#B87936"
        steel = "#7D8992"
        outline = "#606A70"

        layers = [
            ("Seitenholz", timber, 36),
            ("Stahlblech", steel, 14),
            ("Mittelholz", timber_dark, 44),
            ("Stahlblech", steel, 14),
            ("Seitenholz", timber, 36),
        ]
        y = top
        layer_centers = []
        for label, color, h in layers:
            canvas.create_rectangle(x1, y, x2, y + h, fill=color, outline=outline, width=1)
            canvas.create_text(x1 + 12, y + h / 2, text=label, anchor="w", fill="#27323A", font=("Arial", 10, "bold"))
            layer_centers.append(y + h / 2)
            y += h + 4

        rows = 2
        cols = 4
        try:
            cols = max(1, min(self._int("rows_parallel_n"), 6))
            rows = max(1, min(self._int("rows_perpendicular_m"), 3))
        except Exception:
            pass
        start_x = cx - (cols - 1) * 42 / 2
        start_y = top + 28
        total_h = y - top - 4
        for r in range(rows):
            py = start_y + r * ((total_h - 56) / max(rows - 1, 1))
            for c in range(cols):
                px = start_x + c * 42
                canvas.create_oval(px - 7, py - 7, px + 7, py + 7, fill=self.RED, outline="#6E071C", width=2)

        canvas.create_text(
            cx,
            height - 13,
            text="Schematische Darstellung des mehrschnittigen Stabdübelanschlusses",
            fill=self.MUTED,
            font=("Arial", 10),
        )

    # ------------------------------------------------------------------
    # Weitere Seiten
    # ------------------------------------------------------------------

    def _build_placeholder_pages(self) -> None:
        pages = {
            "schraegschrauben": ("Schrägschrauben", "Modul in Entwicklung"),
            "gewindestangen": ("Eingeklebte Gewindestangen", "Modul in Entwicklung"),
            "vergleich": ("Variantenvergleich", "Vergleich von Tragfähigkeit, Ausnutzung und Wirtschaftlichkeit"),
            "berichte": ("Berichte", "Projektberichte und letzte Berechnungen"),
            "einstellungen": ("Einstellungen", "Darstellung, Standards und Projekteinstellungen"),
        }
        for name, (title, subtitle) in pages.items():
            page = self._new_page(name)
            page.grid_columnconfigure(0, weight=1)
            self._page_header(page, title, subtitle).pack(fill="x")
            card = ctk.CTkFrame(page, fg_color=self.CARD, corner_radius=14)
            card.pack(fill="both", expand=True, padx=34, pady=(0, 30))
            ctk.CTkLabel(
                card,
                text="Dieses Modul ist für die nächste Entwicklungsphase vorbereitet.",
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color=self.TEXT,
            ).pack(pady=(100, 12))
            ctk.CTkLabel(
                card,
                text="Die Navigation und Seitenstruktur sind bereits vollständig integriert.",
                font=ctk.CTkFont(size=14),
                text_color=self.MUTED,
            ).pack()

    def _page_header(
        self,
        parent,
        title: str,
        subtitle: str,
        action_text: str | None = None,
        action: Callable[[], None] | None = None,
    ) -> ctk.CTkFrame:
        header = ctk.CTkFrame(parent, fg_color="transparent", height=108)
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text=title,
            font=ctk.CTkFont(size=29, weight="bold"),
            text_color=self.TEXT,
        ).grid(row=0, column=0, sticky="w", padx=34, pady=(25, 3))
        ctk.CTkLabel(
            header,
            text=subtitle,
            font=ctk.CTkFont(size=13),
            text_color=self.MUTED,
        ).grid(row=1, column=0, sticky="w", padx=34, pady=(0, 18))
        if action_text:
            ctk.CTkButton(
                header,
                text=action_text,
                width=125,
                height=38,
                fg_color=self.RED,
                hover_color=self.RED_DARK,
                command=action,
            ).grid(row=0, column=1, rowspan=2, sticky="e", padx=34)
        return header

    def _pdf_placeholder(self) -> None:
        messagebox.showinfo(
            "PDF-Bericht",
            "Die Oberfläche für den PDF-Bericht ist vorbereitet.\n\n"
            "Im nächsten Schritt werden Logo, Projektdaten, Eingaben, "
            "Berechnungsweg, Nachweise, Skizze und Zusammenfassung exportiert.",
        )

    # ------------------------------------------------------------------
    # Daten und Validierung
    # ------------------------------------------------------------------

    def _load_default_values(self) -> None:
        defaults = StabduebelInput()
        for key, entry in self.entries.items():
            if hasattr(defaults, key):
                entry.delete(0, tk.END)
                entry.insert(0, str(getattr(defaults, key)))
        self._draw_connection_sketch()

    def _text(self, key: str) -> str:
        value = self.entries[key].get().strip()
        if not value:
            raise ValueError(f"Das Feld '{key}' darf nicht leer sein.")
        return value

    def _float(self, key: str) -> float:
        value = self.entries[key].get().strip().replace(",", ".")
        if not value:
            raise ValueError(f"Das Feld '{key}' darf nicht leer sein.")
        return float(value)

    def _int(self, key: str) -> int:
        value = self.entries[key].get().strip()
        if not value:
            raise ValueError(f"Das Feld '{key}' darf nicht leer sein.")
        return int(value)

    @staticmethod
    def _validate_float(value: str) -> bool:
        if value in ("", "-", ".", "-."):
            return True
        try:
            float(value.replace(",", "."))
            return True
        except ValueError:
            return False

    @staticmethod
    def _validate_integer(value: str) -> bool:
        return value == "" or value.isdigit()


def main() -> None:
    app = StabduebelApp()
    app.mainloop()


if __name__ == "__main__":
    main()
