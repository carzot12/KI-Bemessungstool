from __future__ import annotations

"""Parametrische Darstellung des vorhandenen Stabdübel-Zuglaschenstoßes."""

from dataclasses import dataclass
import tkinter as tk

import customtkinter as ctk

from calculations.oenorm_validation import ValidationStatus, validate_oenorm
from calculations.stabduebel import StabduebelInput, StabduebelResult


@dataclass(frozen=True, slots=True)
class ConnectionVisualizerData:
    plate_count: int
    shear_planes: int
    plate_thickness_mm: float
    width_mm: float
    height_mm: float
    side_thickness_mm: float
    middle_thickness_mm: float
    slot_allowance_mm: float
    rows_parallel_n: int
    rows_perpendicular_m: int
    diameter_mm: float
    force_ed_kn: float
    a1_mm: float
    a2_mm: float
    a3_t_mm: float
    a4_c_mm: float
    geometry_admissible: bool
    invalid_dimensions: tuple[str, ...]

    @property
    def fastener_count(self) -> int:
        return self.rows_parallel_n * self.rows_perpendicular_m

    @property
    def displayed_fastener_count(self) -> int:
        """Full splice: the calculated grid is shown on both joint sides."""
        return 2 * self.fastener_count

    @property
    def force_label(self) -> str:
        return f"FEd = {self.force_ed_kn:g} kN"

    @property
    def cross_section_layers_mm(self) -> tuple[float, ...]:
        if self.plate_count == 2:
            return (
                self.side_thickness_mm, self.plate_thickness_mm,
                self.middle_thickness_mm, self.plate_thickness_mm,
                self.side_thickness_mm,
            )
        return (
            self.side_thickness_mm, self.plate_thickness_mm,
            self.side_thickness_mm,
        )

    @classmethod
    def from_input(
        cls,
        data: StabduebelInput,
        result: StabduebelResult | None = None,
    ) -> "ConnectionVisualizerData":
        validation = validate_oenorm(data, result)
        geometry_names = {
            "Achsabstand a1",
            "Achsabstand a2",
            "Beanspruchter Endabstand a3,t",
            "Unbeanspruchter Randabstand a4,c",
            "Stabdübeldurchmesser",
            "Anordnung im Querschnitt (Höhe)",
            "Schichtaufbau im Querschnitt (Breite)",
        }
        invalid = tuple(
            check.name for check in validation.checks
            if check.name in geometry_names and check.status is ValidationStatus.FAILED
        )
        return cls(
            plate_count=data.number_of_plates_ns,
            shear_planes=data.shear_planes_s,
            plate_thickness_mm=data.plate_thickness_ts_mm,
            width_mm=data.width_b_mm,
            height_mm=data.height_h_mm,
            side_thickness_mm=data.side_thickness_t1_mm,
            middle_thickness_mm=data.middle_thickness_t2_mm,
            slot_allowance_mm=data.slot_air_per_cut_ts_l_mm,
            rows_parallel_n=data.rows_parallel_n,
            rows_perpendicular_m=data.rows_perpendicular_m,
            diameter_mm=data.dowel_diameter_d_mm,
            force_ed_kn=data.force_ed_kn,
            a1_mm=data.a1_mm,
            a2_mm=data.a2_mm,
            a3_t_mm=data.a3_t_mm,
            a4_c_mm=data.a4_c_mm,
            geometry_admissible=not invalid,
            invalid_dimensions=invalid,
        )


class ConnectionVisualizer(ctk.CTkFrame):
    """Canvas-Visualisierung ohne eigene technische Rechenannahmen."""

    RED = "#B20D30"
    GREEN = "#228B57"
    INK = "#20242A"
    MUTED = "#6B7280"
    WOOD = "#E6C99F"
    WOOD_LINE = "#A77B45"
    STEEL = "#65717F"
    DIMENSION = "#6B7280"

    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, fg_color="#FFFFFF", corner_radius=14, **kwargs)
        self._data: ConnectionVisualizerData | None = None
        self._view = tk.StringVar(value="3D")
        self._show_dimensions = tk.BooleanVar(value=True)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(14, 8))
        ctk.CTkLabel(
            top, text="Technische Live-Visualisierung",
            font=ctk.CTkFont(size=17, weight="bold"), text_color=self.INK,
        ).pack(side="left")
        ctk.CTkSwitch(
            top, text="Maße", variable=self._show_dimensions,
            command=self.redraw, progress_color=self.RED, width=72,
        ).pack(side="right")

        self.selector = ctk.CTkSegmentedButton(
            self, values=["3D", "Seitenansicht", "Querschnitt"],
            variable=self._view, command=lambda _value: self.redraw(),
            selected_color=self.RED, selected_hover_color="#890923",
        )
        self.selector.pack(fill="x", padx=18, pady=(0, 8))

        self.canvas = tk.Canvas(
            self, background="#FAFBFC", highlightthickness=1,
            highlightbackground="#D9DEE5", height=280,
        )
        self.canvas.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.canvas.bind("<Configure>", lambda _event: self.redraw())

        self.caption = ctk.CTkLabel(
            self, text="Noch keine technischen Daten.", anchor="w",
            justify="left", text_color=self.MUTED,
            font=ctk.CTkFont(size=12),
        )
        self.caption.pack(fill="x", padx=18, pady=(0, 14))

    def update_input(
        self,
        data: StabduebelInput,
        result: StabduebelResult | None = None,
    ) -> None:
        self.update_data(ConnectionVisualizerData.from_input(data, result))

    def update_data(self, data: ConnectionVisualizerData) -> None:
        self._data = data
        status = "✓ Geometrie zulässig" if data.geometry_admissible else "✕ Geometrie nicht zulässig"
        details = (
            f"{status}   ·   {data.plate_count} Stahlblech"
            f"{'e' if data.plate_count == 1 else 'e'}   ·   "
            f"{data.shear_planes} Scherfugen"
        )
        if data.invalid_dimensions:
            details += "\nBetroffen: " + ", ".join(data.invalid_dimensions)
        self.caption.configure(
            text=details,
            text_color=self.GREEN if data.geometry_admissible else self.RED,
        )
        self.redraw()

    def clear(self) -> None:
        self._data = None
        self.canvas.delete("all")
        self.caption.configure(text="Noch keine technischen Daten.", text_color=self.MUTED)

    def redraw(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        if self._data is None:
            canvas.create_text(
                max(canvas.winfo_width(), 300) / 2,
                max(canvas.winfo_height(), 220) / 2,
                text="Die Darstellung erscheint nach der ersten Berechnung.",
                fill=self.MUTED,
            )
            return
        if self._view.get() in {"Schnitt", "Querschnitt"}:
            self._draw_cross_section()
        elif self._view.get() == "3D":
            self._draw_isometric_view()
        else:
            self._draw_side_view()

    def _draw_isometric_view(self) -> None:
        data = self._data
        assert data is not None
        c = self.canvas
        width, height = max(c.winfo_width(), 520), max(c.winfo_height(), 300)
        left, seam, right = width * 0.08, width * 0.50, width * 0.86
        top, bottom = height * 0.27, height * 0.78
        depth_x, depth_y = width * 0.09, -height * 0.13

        # Two separate timber members meet at the central end joint.
        for x0, x1, fill in ((left, seam, self.WOOD), (seam, right, "#E9CCA2")):
            c.create_rectangle(x0, top, x1, bottom, fill=fill,
                               outline=self.WOOD_LINE, width=2)
            c.create_polygon(
                x0, top, x1, top, x1 + depth_x, top + depth_y,
                x0 + depth_x, top + depth_y,
                fill="#F1D8B2", outline=self.WOOD_LINE, width=2,
            )
        c.create_line(seam, top, seam, bottom, fill="#704B2D", width=3)
        c.create_line(seam + depth_x, top + depth_y, seam, top,
                      fill="#704B2D", width=2)

        # Slotted internal plates appear only as narrow planes on the opened
        # top projection and bridge the joint; they are never external straps.
        if data.plate_count == 1:
            fractions = (0.5,)
        else:
            fractions = (
                (data.side_thickness_mm + data.plate_thickness_mm / 2) / data.width_mm,
                (data.side_thickness_mm + data.plate_thickness_mm
                 + data.middle_thickness_mm + data.plate_thickness_mm / 2) / data.width_mm,
            )
        plate_span = (right - left) * 0.58
        for fraction in fractions:
            ox, oy = depth_x * fraction, depth_y * fraction
            c.create_line(
                seam - plate_span / 2 + ox, top + oy,
                seam + plate_span / 2 + ox, top + oy,
                fill=self.STEEL, width=max(2, int(data.plate_thickness_mm / 2)),
            )
            c.create_line(
                seam - plate_span / 2 + ox, top + oy - 3,
                seam + plate_span / 2 + ox, top + oy - 3,
                fill="#3F4852", width=1, dash=(6, 4),
            )

        left_xs, right_xs = self._splice_x_positions(
            left, seam, right, data.rows_parallel_n
        )
        ys = self._positions(top + (bottom - top) * 0.23,
                             bottom - (bottom - top) * 0.18,
                             data.rows_perpendicular_m)
        radius = max(3.0, min(9.0, data.diameter_mm * (bottom - top) / data.height_mm / 2))
        for y in ys:
            for x in (*left_xs, *right_xs):
                c.create_oval(x - radius, y - radius, x + radius, y + radius,
                              fill="#F8FAFC", outline=self.INK, width=2,
                              tags=("dowel", "isometric_dowel"))
        c.create_text(
            width / 2, 18,
            text=(f"Innenliegende Schlitzbleche · {data.rows_parallel_n} × "
                  f"{data.rows_perpendicular_m} = {data.fastener_count} je Stoßseite"),
            fill=self.INK, font=("Arial", 11, "bold"),
        )
        if self._show_dimensions.get():
            c.create_text(
                width / 2, height - 18,
                text=(f"b = {data.width_mm:g} mm · h = {data.height_mm:g} mm · "
                      f"ts = {data.plate_thickness_mm:g} mm · Ø{data.diameter_mm:g} mm"),
                fill=self.DIMENSION, font=("Arial", 9),
            )

    def _draw_side_view(self) -> None:
        data = self._data
        assert data is not None
        c = self.canvas
        width, height = max(c.winfo_width(), 400), max(c.winfo_height(), 240)
        left, seam, right = width * 0.10, width * 0.50, width * 0.90
        top, bottom = height * 0.18, height * 0.78
        c.create_rectangle(left, top, seam, bottom, fill=self.WOOD, outline=self.WOOD_LINE, width=2)
        c.create_rectangle(seam, top, right, bottom, fill="#E9CCA2", outline=self.WOOD_LINE, width=2)
        c.create_line(seam, top, seam, bottom, fill="#704B2D", width=3,
                      tags=("joint",))
        c.create_text(seam, top - 27, text="Stoßfuge", fill="#704B2D", font=("Arial", 9, "bold"))

        # Hidden internal plate extent, deliberately subtle and dashed.
        hidden_half = (right - left) * 0.28
        for offset in range(data.plate_count):
            inset = 6 + offset * 5
            c.create_rectangle(
                seam - hidden_half, top + inset, seam + hidden_half, bottom - inset,
                outline="#87919C", dash=(7, 5), width=1,
            )

        # Kraftpfeile zeigen den ausschließlich unterstützten Zugfall.
        mid_y = (top + bottom) / 2
        c.create_line(left, mid_y, 18, mid_y, arrow=tk.LAST, width=3, fill=self.RED)
        c.create_line(right, mid_y, width - 18, mid_y, arrow=tk.LAST, width=3, fill=self.RED)
        c.create_text(width / 2, 25, text=data.force_label, fill=self.INK, font=("Arial", 12, "bold"))
        c.create_text(left - 8, mid_y - 16, text="FEd", fill=self.RED, font=("Arial", 9, "bold"))
        c.create_text(right + 8, mid_y - 16, text="FEd", fill=self.RED, font=("Arial", 9, "bold"))
        c.create_line(left + 18, top + 16, right - 18, top + 16, arrow=tk.LAST,
                      fill=self.WOOD_LINE, width=2)
        c.create_text((left + right) / 2, top + 29, text="Faserrichtung",
                      fill=self.WOOD_LINE, font=("Arial", 9, "bold"))

        y_margin = max(22.0, min(40.0, (bottom - top) * 0.22))
        left_xs, right_xs = self._splice_x_positions(left, seam, right, data.rows_parallel_n)
        ys = self._positions(top + y_margin, bottom - y_margin, data.rows_perpendicular_m)
        base = min((seam - left) / max(data.rows_parallel_n + 2, 4), (bottom - top) / max(data.rows_perpendicular_m + 2, 4))
        radius = max(4.0, min(12.0, base * 0.22 * data.diameter_mm / 12.0))
        for y in ys:
            for x in (*left_xs, *right_xs):
                c.create_oval(
                    x - radius, y - radius, x + radius, y + radius,
                    fill="#F7F8FA", outline=self.INK, width=2,
                    tags=("dowel", "side_dowel"),
                )
                c.create_oval(x - 1.5, y - 1.5, x + 1.5, y + 1.5, fill=self.INK, outline="")

        c.create_text(
            width / 2, height - 43,
            text=(f"{data.rows_parallel_n} × {data.rows_perpendicular_m} = "
                  f"{data.fastener_count} je Stoßseite · dargestellt {data.displayed_fastener_count}   ·   Ø{data.diameter_mm:g} mm"),
            fill=self.INK, font=("Arial", 11, "bold"),
        )
        if self._show_dimensions.get():
            dim_color = self.RED if data.invalid_dimensions else self.DIMENSION
            if len(left_xs) >= 2:
                self._dimension_line(c, left_xs[0], bottom + 13, left_xs[1], bottom + 13,
                                     f"a1 = {data.a1_mm:g}", dim_color)
            if len(ys) >= 2:
                self._dimension_line(c, right + 13, ys[0], right + 13, ys[1],
                                     f"a2 = {data.a2_mm:g}", dim_color)
            self._dimension_line(c, left_xs[-1], top - 13, seam, top - 13,
                                 f"a3,t = {data.a3_t_mm:g}", dim_color)
            self._dimension_line(c, left - 13, top, left - 13, ys[0],
                                 f"a4,c = {data.a4_c_mm:g}", dim_color)
            self._dimension_line(c, right + 42, top, right + 42, bottom,
                                 f"h = {data.height_mm:g} mm", dim_color)
            c.create_text(
                width / 2, height - 13,
                text="a3,c und a4,t: im V1-Eingabemodell nicht separat vorhanden",
                fill=dim_color, font=("Arial", 8),
            )

    def _draw_cross_section(self) -> None:
        data = self._data
        assert data is not None
        c = self.canvas
        width, height = max(c.winfo_width(), 400), max(c.winfo_height(), 240)
        box_w = width * 0.86
        box_h = height * 0.58
        x0, x1 = (width - box_w) / 2, (width + box_w) / 2
        y0, y1 = height * 0.16, height * 0.16 + box_h
        c.create_rectangle(x0, y0, x1, y1, fill=self.WOOD, outline=self.WOOD_LINE, width=2)

        scale_x = box_w / data.width_mm
        technical_plate_width = data.plate_thickness_mm * scale_x
        plate_width = max(1.0, technical_plate_width)
        if data.plate_count == 1:
            plate_centres = [x0 + data.side_thickness_mm * scale_x + technical_plate_width / 2]
        else:
            first = x0 + data.side_thickness_mm * scale_x + technical_plate_width / 2
            second = first + technical_plate_width + data.middle_thickness_mm * scale_x
            plate_centres = [first, second]
        for centre in plate_centres:
            c.create_rectangle(
                centre - plate_width / 2, y0 + 2, centre + plate_width / 2, y1 - 2,
                fill=self.STEEL, outline="#3F4852", tags=("internal_plate",),
            )

        ys = self._positions(y0 + box_h * 0.2, y1 - box_h * 0.2, data.rows_perpendicular_m)
        for y in ys:
            c.create_line(
                x0 + 4, y, x1 - 4, y, fill=self.INK, width=2,
                dash=(7, 5), tags=("section_dowel_axis",),
            )

        c.create_text(width / 2, 20, text="Eingeschlitztes Stahlblech im Holzquerschnitt", fill=self.INK, font=("Arial", 11, "bold"))
        if self._show_dimensions.get():
            cursor = x0
            labels = (
                ["t1", "ts", "t2", "ts", "t1"]
                if data.plate_count == 2 else ["t1", "ts", "t1"]
            )
            for layer, label in zip(data.cross_section_layers_mm, labels):
                next_x = cursor + layer * scale_x
                self._dimension_line(
                    c, cursor, y1 + 14, next_x, y1 + 14,
                    f"{label}={layer:g}", self.DIMENSION,
                )
                cursor = next_x
            self._dimension_line(
                c, x0, y0 - 14, x1, y0 - 14,
                f"b = {data.width_mm:g} mm", self.DIMENSION,
            )
            self._dimension_line(
                c, x1 + 18, y0, x1 + 18, y1,
                f"h = {data.height_mm:g} mm", self.DIMENSION,
            )
        c.create_text(
            width / 2, y1 + 34,
            text=(f"b = {data.width_mm:g} mm   ·   h = {data.height_mm:g} mm   ·   "
                  f"t = {data.plate_thickness_mm:g} mm   ·   {data.shear_planes} Scherfugen"),
            fill=self.INK, font=("Arial", 10),
        )
        if data.plate_count == 2:
            build_up = (
                f"Aufbau: {data.side_thickness_mm:g} | {data.plate_thickness_mm:g} | "
                f"{data.middle_thickness_mm:g} | {data.plate_thickness_mm:g} | "
                f"{data.side_thickness_mm:g} mm"
            )
        else:
            build_up = (
                f"Aufbau: {data.side_thickness_mm:g} | {data.plate_thickness_mm:g} | "
                f"{data.side_thickness_mm:g} mm"
            )
        c.create_text(
            width / 2, y1 + 51,
            text=build_up + f"   ·   ts,L = {data.slot_allowance_mm:g} mm",
            fill=self.MUTED, font=("Arial", 9),
        )

    @staticmethod
    def _positions(start: float, end: float, count: int) -> list[float]:
        if count <= 1:
            return [(start + end) / 2]
        return [start + index * (end - start) / (count - 1) for index in range(count)]

    @classmethod
    def _splice_x_positions(
        cls, left: float, seam: float, right: float, count: int,
    ) -> tuple[list[float], list[float]]:
        """Return one calculated n-column grid on each side of the end joint."""
        left_span = seam - left
        right_span = right - seam
        left_grid = cls._positions(left + left_span * 0.24, seam - left_span * 0.18, count)
        right_grid = [2 * seam - x for x in reversed(left_grid)]
        if abs(right_span - left_span) > 1e-6:
            right_grid = cls._positions(seam + right_span * 0.18, right - right_span * 0.24, count)
        return left_grid, right_grid

    @staticmethod
    def _dimension_line(
        canvas: tk.Canvas,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        label: str,
        color: str,
    ) -> None:
        canvas.create_line(x0, y0, x1, y1, fill=color, arrow=tk.BOTH, width=1)
        canvas.create_text(
            (x0 + x1) / 2,
            (y0 + y1) / 2 - (8 if abs(x1 - x0) >= abs(y1 - y0) else 0),
            text=label,
            fill=color,
            font=("Arial", 8),
        )
