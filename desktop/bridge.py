from __future__ import annotations

import os
import sys
import subprocess
import logging
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from threading import RLock
from typing import Any

from ai.assistant import StabduebelAssistant
from calculations.stabduebel import StabduebelInput, calculate_stabduebel
from infopol.materials import (
    LOAD_DURATION_CLASSES,
    get_connection_gamma_m,
    get_kmod,
)
from ai.optimizer import curated_feasible_variants

from .serializers import DemoSnapshot, build_demo_snapshot, serialize_snapshot
from .reports import create_report


LOGGER = logging.getLogger(__name__)


class DesktopBridge:
    """Small allow-listed bridge. Python remains the single source of truth."""

    def __init__(self, *, demo_enabled: bool | None = None) -> None:
        self.assistant = StabduebelAssistant()
        use_demo = (
            demo_enabled
            if demo_enabled is not None
            else os.getenv("KI_TOOL_DEMO_SNAPSHOT", "0") == "1"
        )
        self.demo: DemoSnapshot | None = build_demo_snapshot() if use_demo else None
        self.conversation: list[dict[str, str]] = [{
            "role": "assistant",
            "content": "Willkommen! Beschreibe deinen Zuglaschenstoß oder starte mit der Kompakt- bzw. manuellen Eingabe.",
        }]
        self._revision = 0
        self._lock = RLock()

    def _envelope(self) -> dict[str, Any]:
        self._revision += 1
        return {
            "ok": True,
            "revision": self._revision,
            "data": serialize_snapshot(
                self.assistant, self.conversation, demo=self.demo,
            ),
            "error": None,
        }

    @staticmethod
    def _brief_result_text(reply: Any, previous_result: Any = None) -> str:
        if reply.result is None:
            return reply.text
        data = reply.result.input
        count = data.rows_parallel_n * data.rows_perpendicular_m
        status = "erfüllt" if reply.result.passed else "nicht erfüllt"
        summary = (
            f"Ich würde hier Ø{data.dowel_diameter_d_mm:g} mm mit {count} Stabdübeln "
            f"({data.rows_parallel_n} × {data.rows_perpendicular_m}) wählen. "
            f"Der Rechenkern bewertet den Nachweis als {status}. "
        )
        if previous_result is not None and previous_result is not reply.result:
            before = previous_result.governing_check.utilization * 100
            after = reply.result.governing_check.utilization * 100
            direction = "sinkt" if after < before else "ändert sich"
            summary += (
                f"Die maximale Ausnutzung {direction} von {before:.1f} % auf "
                f"{after:.1f} %; maßgebend ist „{reply.result.governing_check.name}“."
            )
        else:
            summary += "Details und berechnete Alternativen findest du rechts."
        return summary

    def bootstrap(self) -> dict[str, Any]:
        with self._lock:
            return self._envelope()

    def reset_design(self) -> dict[str, Any]:
        """Start a genuinely empty design while preserving app-level settings."""
        with self._lock:
            self.assistant = StabduebelAssistant()
            self.demo = None
            self.conversation = [{
                "role": "assistant",
                "content": "Neuer Entwurf gestartet. Welche Verbindung soll ich bemessen?",
            }]
            return self._envelope()

    def _error(self, message: str) -> dict[str, Any]:
        return {
            "ok": False,
            "revision": self._revision,
            "data": serialize_snapshot(self.assistant, self.conversation, demo=self.demo),
            "error": message,
        }

    def send_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text", "")).strip()
        if not text:
            return {"ok": False, "revision": self._revision, "data": None,
                    "error": "Die Nachricht ist leer."}
        with self._lock:
            self.conversation.append({"role": "user", "content": text})
            try:
                previous_result = self.assistant.state.last_result
                previous_optimization = self.assistant.state.last_optimization
                reply = self.assistant.respond(text)
                design_changed = (
                    self.assistant.state.last_result != previous_result
                    or self.assistant.state.last_optimization != previous_optimization
                )
                self.conversation.append({
                    "role": "assistant",
                    "content": self._brief_result_text(reply, previous_result) if design_changed else reply.text,
                })
                return self._envelope()
            except Exception as exc:
                self.conversation.append({
                    "role": "assistant",
                    "content": f"Der Agent konnte die Anfrage nicht abschließen: {exc}",
                })
                response = self._envelope()
                response["ok"] = False
                response["error"] = str(exc)
                return response

    def copy_chat_text(self) -> str:
        return "\n\n".join(
            f"{'Sie' if item['role'] == 'user' else 'Assistent'}:\n{item['content']}"
            for item in self.conversation
        )

    def form_options(self) -> dict[str, Any]:
        """UI choices and defaults sourced from the existing Python model."""
        return {
            "timberGrades": list(self.assistant.materials.grades()),
            "loadDurations": list(LOAD_DURATION_CLASSES),
            "manualDefaults": asdict(StabduebelInput()),
        }

    def set_llm_provider(self, payload: dict[str, Any]) -> dict[str, Any]:
        provider = str(payload.get("provider") or "").strip().lower()
        with self._lock:
            try:
                self.assistant.set_llm_provider(provider)
            except ValueError as exc:
                return self._error(str(exc))
            return self._envelope()

    def manual_example(self) -> dict[str, Any]:
        """Return the explicit reference input without mutating the design state."""
        return {"ok": True, "data": asdict(StabduebelInput()), "error": None}

    def create_pdf_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        report_type = str(payload.get("type") or "calculation")
        if report_type not in {"calculation", "variants"}:
            return {"status": "error", "message": "Unbekannter Berichtstyp."}
        with self._lock:
            snapshot = serialize_snapshot(
                self.assistant, self.conversation, demo=self.demo,
            )
            project = str(snapshot.get("projectName") or "").strip()
            safe_project = "".join(
                "_" if character in '/\\:\0' else character
                for character in project
            ).strip(" .")
            default_name = (
                f"{safe_project}.pdf" if safe_project
                else "KI_Bemessungstool_Bericht.pdf"
            )
            try:
                import webview
                windows = webview.windows
                if windows:
                    LOGGER.info("[PDF] opening save dialog; default=%s", default_name)
                    chosen = windows[0].create_file_dialog(
                        webview.SAVE_DIALOG,
                        save_filename=default_name,
                        # pywebview 6.2.1 validates the description with
                        # ``[\w ]+``. A hyphen (as in "PDF-Dateien") makes
                        # an otherwise correct macOS filter invalid.
                        file_types=("PDF (*.pdf)",),
                    )
                    LOGGER.info("[PDF] save dialog result: %r", chosen)
                    if not chosen:
                        LOGGER.info("[PDF] save dialog cancelled")
                        return {"status": "cancelled"}
                    if isinstance(chosen, (list, tuple)):
                        if not chosen or not chosen[0]:
                            LOGGER.info("[PDF] save dialog returned an empty selection")
                            return {"status": "cancelled"}
                        selected_path = chosen[0]
                    else:
                        selected_path = chosen
                    target = Path(os.path.expanduser(str(selected_path)))
                    if target.suffix.lower() != ".pdf":
                        target = target.with_suffix(".pdf")
                    LOGGER.info("[PDF] resolved path: %s", target)
                else:
                    return {
                        "status": "error",
                        "message": "Kein natives Speicherfenster verfügbar.",
                    }
                LOGGER.info("[PDF] ensuring directory: %s", target.parent)
                target.parent.mkdir(parents=True, exist_ok=True)
                LOGGER.info("[PDF] building report at exact selected path: %s", target)
                target = create_report(
                    snapshot, report_type, target.parent,
                    filename=target.name,
                )
                exists = target.is_file()
                size = target.stat().st_size if exists else 0
                LOGGER.info("[PDF] file exists after build: %s", exists)
                LOGGER.info("[PDF] file size: %s", size if exists else None)
                if not exists:
                    return {
                        "status": "error",
                        "message": f"PDF wurde nicht erstellt: {target}",
                    }
                if size <= 0:
                    return {
                        "status": "error",
                        "message": f"PDF ist leer: {target}",
                    }
            except Exception as exc:
                LOGGER.exception("PDF-Bericht konnte nicht erstellt werden")
                return {
                    "status": "error",
                    "message": f"{type(exc).__name__}: {exc}",
                }
        return {"status": "success", "path": str(target), "size": size}

    def open_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(payload.get("path", ""))).expanduser()
        if not path.is_file():
            return {"ok": False, "error": "Die PDF-Datei wurde nicht gefunden."}
        subprocess.run(["open", str(path)], check=True)
        return {"ok": True, "error": None}

    def reveal_report(self, payload: dict[str, Any]) -> dict[str, Any]:
        path = Path(str(payload.get("path", ""))).expanduser()
        if not path.is_file():
            return {"ok": False, "error": "Die PDF-Datei wurde nicht gefunden."}
        subprocess.run(["open", "-R", str(path)], check=True)
        return {"ok": True, "error": None}

    def set_report_selection(self, payload: dict[str, Any]) -> dict[str, Any]:
        ids = payload.get("variant_ids", [])
        if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
            return self._error("Ungültige Berichtsauswahl.")
        with self._lock:
            self.assistant.state.report_variant_ids = set(ids)
            return self._envelope()

    def set_project_name(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("project_name", "")).strip()
        with self._lock:
            self.assistant.state.parameters["project_name"] = name
            if self.assistant.state.last_result:
                self.assistant.state.last_result.input.project_name = name
            return self._envelope()

    def adopt_variant(self, payload: dict[str, Any]) -> dict[str, Any]:
        variant_id = str(payload.get("variant_id", ""))
        if not variant_id.startswith("variant-"):
            return self._error("Ungültige Variante.")
        try:
            index = int(variant_id.removeprefix("variant-")) - 1
        except ValueError:
            return self._error("Ungültige Variante.")
        with self._lock:
            candidates = (
                [item.result for item in curated_feasible_variants(
                    self.assistant.state.last_optimization,
                    self.assistant.state.optimization_goal,
                    self.assistant.state.fixed_parameters,
                    12,
                )]
                if self.assistant.state.last_optimization else
                ([self.demo.result, *self.demo.variants[1:]] if self.demo else [])
            )
            if index < 0 or index >= len(candidates):
                return self._error("Die Variante ist nicht verfügbar.")
            project_name = str(
                self.assistant.state.parameters.get("project_name") or
                (self.assistant.state.last_result.input.project_name
                 if self.assistant.state.last_result else "")
            )
            result = deepcopy(candidates[index])
            if project_name:
                result.input.project_name = project_name
            self.assistant.state.last_result = result
            self.assistant.state.last_successful_result = result if result.passed else None
            self.assistant.state.parameters = asdict(result.input)
            self.assistant.state.last_recommendation = (
                f"Aktuelle Variante: Ø{result.input.dowel_diameter_d_mm:g} mm"
            )
            return self._envelope()

    def compact_calculate(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            objective = str(payload.get("objective") or "BALANCED_DESIGN")
            force = float(payload["force_ed_kn"])
            width = float(payload["width_b_mm"])
            height = float(payload["height_h_mm"])
            service_class = int(payload["service_class"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            return self._error(f"Ungültige Eingabe: {exc}")
        goal = {
            "BALANCED_DESIGN": "mach mir einen sinnvollen wirtschaftlichen Entwurf",
            "MIN_FASTENER_COUNT": "möglichst wenige Stabdübel",
            "LOWER_UTILIZATION": "mehr Reserve",
            "COMPACT_GEOMETRY": "möglichst kompakte Geometrie",
            "MAXIMIZE_UTILIZATION": "maximal ausnutzen",
        }.get(objective, "mach mir einen sinnvollen wirtschaftlichen Entwurf")
        prompt = (
            f"{force:g} kN {payload['timber_grade']} "
            f"{width:g}x{height:g} mm "
            f"NK{service_class} {payload['load_duration_class']}, "
            f"{goal}, rest mach selber"
        )
        with self._lock:
            # The structured design brief is authoritative; do not rely on a
            # second natural-language interpretation of its selected goal.
            self.assistant.state.optimization_goal = objective
            self.assistant.state.minimize_fasteners = objective == "MIN_FASTENER_COUNT"
            self.assistant.state.maximize_utilization = objective == "MAXIMIZE_UTILIZATION"
            self.conversation.append({"role": "user", "content": prompt})
            reply = self.assistant.execute_local_command(prompt)
            if payload.get("project_name"):
                self.assistant.state.parameters["project_name"] = str(payload["project_name"])
                if self.assistant.state.last_result:
                    self.assistant.state.last_result.input.project_name = str(payload["project_name"])
            self.conversation.append({
                "role": "assistant", "content": self._brief_result_text(reply),
            })
            return self._envelope()

    def manual_calculate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Manual UI adapter; all engineering remains in the existing core."""
        with self._lock:
            defaults = asdict(StabduebelInput())
            values = {**defaults, **payload}
            grade = str(values["timber_grade"])
            service_class = int(values["service_class"])
            duration = str(values["load_duration_class"])
            try:
                material = self.assistant.materials.get(grade)
                values.update(
                    timber_grade=grade,
                    service_class=service_class,
                    load_duration_class=duration,
                    k_mod=get_kmod(material, service_class, duration),
                    gamma_m_timber=get_connection_gamma_m(),
                    rho_k_kg_m3=material.value("rho_k"),
                    ft_0_k_n_mm2=material.value("ft_0_k"),
                    fv_k_n_mm2=material.value("fv_k"),
                )
                result = calculate_stabduebel(StabduebelInput(**values))
            except (KeyError, TypeError, ValueError, OverflowError, LookupError) as exc:
                return self._error(f"Eingabe konnte nicht berechnet werden: {exc}")
            self.assistant.state.previous_technical_state = dict(
                self.assistant.state.parameters
            )
            self.assistant.state.parameters = asdict(result.input)
            self.assistant.state.fixed_parameters = set(payload)
            self.assistant.state.parameter_provenance.update(
                {key: "USER_FIXED" for key in payload}
            )
            self.assistant.state.last_result = result
            self.assistant.state.last_successful_result = result if result.passed else None
            self.assistant._set_connection_state(result.input.number_of_plates_ns)
            self.demo = None
            return self._envelope()
