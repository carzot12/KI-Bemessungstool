from __future__ import annotations

import os
from dataclasses import asdict
from threading import RLock
from typing import Any

from ai.assistant import StabduebelAssistant
from calculations.stabduebel import StabduebelInput, calculate_stabduebel
from infopol.materials import (
    LOAD_DURATION_CLASSES,
    get_connection_gamma_m,
    get_kmod,
)

from .serializers import DemoSnapshot, build_demo_snapshot, serialize_snapshot


class DesktopBridge:
    """Small allow-listed bridge. Python remains the single source of truth."""

    def __init__(self, *, demo_enabled: bool | None = None) -> None:
        self.assistant = StabduebelAssistant()
        use_demo = (
            demo_enabled
            if demo_enabled is not None
            else os.getenv("KI_TOOL_DEMO_SNAPSHOT", "1") != "0"
        )
        self.demo: DemoSnapshot | None = build_demo_snapshot() if use_demo else None
        self.conversation: list[dict[str, str]] = [{
            "role": "assistant",
            "content": "Willkommen im neuen Engineering Workspace. Der Python-Kern ist verbunden.",
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

    def bootstrap(self) -> dict[str, Any]:
        with self._lock:
            return self._envelope()

    def send_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text", "")).strip()
        if not text:
            return {"ok": False, "revision": self._revision, "data": None,
                    "error": "Die Nachricht ist leer."}
        with self._lock:
            self.conversation.append({"role": "user", "content": text})
            try:
                reply = self.assistant.respond(text)
                self.conversation.append({"role": "assistant", "content": reply.text})
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

    def compact_calculate(self, payload: dict[str, Any]) -> dict[str, Any]:
        objective = str(payload.get("objective") or "BALANCED_DESIGN")
        goal = {
            "BALANCED_DESIGN": "mach mir einen sinnvollen wirtschaftlichen Entwurf",
            "MIN_FASTENER_COUNT": "möglichst wenige Stabdübel",
            "LOWER_UTILIZATION": "mehr Reserve",
            "COMPACT_GEOMETRY": "möglichst kompakte Geometrie",
            "MAXIMIZE_UTILIZATION": "maximal ausnutzen",
        }.get(objective, "mach mir einen sinnvollen wirtschaftlichen Entwurf")
        prompt = (
            f"{float(payload['force_ed_kn']):g} kN {payload['timber_grade']} "
            f"{float(payload['width_b_mm']):g}x{float(payload['height_h_mm']):g} mm "
            f"NK{int(payload['service_class'])} {payload['load_duration_class']}, "
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
            self.conversation.append({"role": "assistant", "content": reply.text})
            return self._envelope()

    def manual_calculate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Manual UI adapter; all engineering remains in the existing core."""
        with self._lock:
            defaults = asdict(StabduebelInput())
            values = {**defaults, **payload}
            grade = str(values["timber_grade"])
            service_class = int(values["service_class"])
            duration = str(values["load_duration_class"])
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
