from __future__ import annotations

"""LLM-first orchestration around the existing deterministic engineering code."""

import json
import logging
from dataclasses import asdict
from typing import Any, Callable

from calculations.oenorm_validation import validate_oenorm
from knowledge.sources import find_sources, get_knowledge


LOGGER = logging.getLogger("ki_bemessungstool.agent")


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function", "name": "get_current_design",
        "description": "Return the current technical design and result.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function", "name": "update_design",
        "description": "Apply user or knowledge-derived design parameters without calculating values yourself.",
        "parameters": {
            "type": "object",
            "properties": {
                "parameters": {"type": "object", "additionalProperties": True},
                "provenance": {"type": "string", "enum": ["USER_FIXED", "AI_DERIVED", "KNOWLEDGE_DERIVED"]},
                "source": {"type": ["string", "null"]},
                "autonomy_mode": {"type": ["boolean", "null"]},
            },
            "required": ["parameters", "provenance", "source", "autonomy_mode"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function", "name": "calculate_design",
        "description": "Calculate the current design only through the existing Python core.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function", "name": "optimize_design",
        "description": "Run the existing deterministic variant optimizer.",
        "parameters": {
            "type": "object",
            "properties": {
                "objective": {"type": "string"},
                "constraints": {"type": "object", "additionalProperties": True},
            },
            "required": ["objective", "constraints"], "additionalProperties": False,
        },
    },
    {
        "type": "function", "name": "compare_variants",
        "description": "Compare only variants/results already calculated by Python.",
        "parameters": {
            "type": "object", "properties": {
                "variant_ids": {"type": "array", "items": {"type": "integer"}},
                "constraints": {"type": "object", "additionalProperties": True},
            }, "required": ["variant_ids", "constraints"], "additionalProperties": False,
        },
    },
    {
        "type": "function", "name": "calculate_maximum_load",
        "description": "Calculate maximum load through repeated existing-core calls.",
        "parameters": {"type": "object", "properties": {"constraints": {"type": "object", "additionalProperties": True}}, "required": ["constraints"], "additionalProperties": False},
    },
    {
        "type": "function", "name": "validate_design",
        "description": "Run the existing OENORM validator on the current calculated design.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function", "name": "get_previous_design",
        "description": "Return the previous design and result.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function", "name": "restore_previous_design",
        "description": "Undo the last design change.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function", "name": "get_missing_information",
        "description": "Return genuinely missing information for deterministic calculation.",
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "type": "function", "name": "search_knowledge_base",
        "description": "Search verified local engineering sources. Use this for technical questions and classifications.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False},
    },
    {
        "type": "function", "name": "explain_calculation",
        "description": "Return deterministic facts for explaining a calculated check or selection.",
        "parameters": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"], "additionalProperties": False},
    },
]


def _result_summary(result: Any) -> dict[str, Any] | None:
    if result is None:
        return None
    data = result.input
    validation = validate_oenorm(data, result)
    return {
        "input": asdict(data),
        "passed": result.passed,
        "norm_admissible": validation.admissible,
        "governing_check": asdict(result.governing_check),
        "checks": [asdict(item) for item in result.checks],
        "validation_failures": [asdict(item) for item in validation.failures],
    }


class EngineeringTools:
    """Thin facade. It coordinates existing code and contains no formulas."""

    ALIASES = {
        "force_kn": "force_ed_kn", "force_ed_kn": "force_ed_kn",
        "timber_grade": "timber_grade", "dowel_diameter_mm": "dowel_diameter_d_mm",
        "dowel_diameter_d_mm": "dowel_diameter_d_mm", "plate_count": "number_of_plates_ns",
        "number_of_plates_ns": "number_of_plates_ns", "plate_thickness_mm": "plate_thickness_ts_mm",
        "plate_thickness_ts_mm": "plate_thickness_ts_mm", "width_mm": "width_b_mm",
        "width_b_mm": "width_b_mm", "height_mm": "height_h_mm", "height_h_mm": "height_h_mm",
        "side_thickness_mm": "side_thickness_t1_mm", "side_thickness_t1_mm": "side_thickness_t1_mm",
        "middle_thickness_mm": "middle_thickness_t2_mm", "middle_thickness_t2_mm": "middle_thickness_t2_mm",
        "slot_allowance_mm": "slot_air_per_cut_ts_l_mm", "slot_air_per_cut_ts_l_mm": "slot_air_per_cut_ts_l_mm",
        "service_class": "service_class", "load_duration_class": "load_duration_class",
        "rows_parallel_n": "rows_parallel_n", "rows_perpendicular_m": "rows_perpendicular_m",
        "total_fastener_count": "total_fastener_count", "max_utilization": "max_utilization",
    }

    def __init__(self, assistant: Any) -> None:
        self.assistant = assistant
        self.last_reply: Any = None

    def dispatch(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        handler: Callable[..., dict[str, Any]] | None = getattr(self, name, None)
        if handler is None or name.startswith("_"):
            raise ValueError(f"Unbekanntes Engineering-Tool: {name}")
        return handler(**arguments)

    def get_current_design(self) -> dict[str, Any]:
        return self.assistant.agent_context()

    def update_design(self, parameters: dict[str, Any], provenance: str, source: str | None, autonomy_mode: bool | None) -> dict[str, Any]:
        unknown = sorted(set(parameters) - set(self.ALIASES))
        if unknown:
            raise ValueError("Nicht unterstützte Parameter: " + ", ".join(unknown))
        extracted = self.assistant.empty_parameter_update()
        mapped = {self.ALIASES[key]: value for key, value in parameters.items()}
        if provenance != "USER_FIXED":
            mapped = {
                key: value for key, value in mapped.items()
                if key not in self.assistant.state.fixed_parameters
            }
        extracted.update(mapped)
        self.assistant._undo_state = self.assistant.copy_state()
        self.assistant._apply(extracted)
        if autonomy_mode is not None:
            self.assistant.state.autonomy_mode = autonomy_mode
        if provenance != "USER_FIXED":
            for key in mapped:
                self.assistant.state.fixed_parameters.discard(key)
                self.assistant.state.parameter_provenance[key] = provenance
                if source:
                    self.assistant.state.parameter_sources[key] = source
        return {"updated": mapped, "provenance": provenance, "design": self.assistant.agent_context()["current_design"]}

    def calculate_design(self) -> dict[str, Any]:
        self.last_reply = self.assistant.execute_local_command("bemesse den aktuellen Anschluss")
        return {"result": _result_summary(self.last_reply.result), "missing_information": self.assistant._missing_required_parameters()}

    def optimize_design(self, objective: str, constraints: dict[str, Any]) -> dict[str, Any]:
        if constraints:
            self.update_design(constraints, "USER_FIXED", None, True)
        self.assistant.state.autonomy_mode = True
        objectives = {
            "MIN_FASTENER_COUNT": "MIN_FASTENER_COUNT", "FEWER_FASTENERS": "MIN_FASTENER_COUNT",
            "LOWER_UTILIZATION": "LOWER_UTILIZATION", "MORE_RESERVE": "LOWER_UTILIZATION",
            "COMPACT_GEOMETRY": "COMPACT_GEOMETRY", "MIN_PLATE_THICKNESS": "MIN_PLATE_THICKNESS",
            "BALANCED_DESIGN": "BALANCED_DESIGN",
        }
        normalized = objectives.get(objective.upper(), objective.upper())
        self.assistant.state.optimization_goal = normalized
        self.assistant.state.minimize_fasteners = normalized == "MIN_FASTENER_COUNT"
        self.last_reply = self.assistant.execute_local_command("optimiere den aktuellen Entwurf")
        optimization = self.assistant.state.last_optimization
        return {
            "objective": normalized, "result": _result_summary(self.last_reply.result),
            "evaluated_count": optimization.evaluated_count if optimization else 0,
            "feasible_count": optimization.feasible_count if optimization else 0,
            "considered_variants": self.assistant.compact_variants(),
        }

    def compare_variants(self, variant_ids: list[int], constraints: dict[str, Any]) -> dict[str, Any]:
        if constraints:
            self.update_design(constraints, "USER_FIXED", None, None)
        variants = self.assistant.compact_variants()
        chosen = [item for item in variants if not variant_ids or item["id"] in variant_ids]
        return {"variants": chosen, "note": "Only actually calculated variants are returned."}

    def calculate_maximum_load(self, constraints: dict[str, Any]) -> dict[str, Any]:
        if constraints:
            self.update_design(constraints, "USER_FIXED", None, None)
        return {"deterministic_result": self.assistant._maximum_load_text()}

    def validate_design(self) -> dict[str, Any]:
        result = self.assistant.state.last_result
        if result is None:
            return {"available": False, "missing_information": self.assistant._missing_required_parameters()}
        validation = validate_oenorm(result.input, result)
        return {"available": True, "admissible": validation.admissible, "checks": [asdict(item) for item in validation.checks]}

    def get_previous_design(self) -> dict[str, Any]:
        previous = self.assistant.conversation.previous_result
        return {"previous_design": asdict(previous.input) if previous else self.assistant.state.previous_technical_state, "previous_result": _result_summary(previous)}

    def restore_previous_design(self) -> dict[str, Any]:
        self.last_reply = self.assistant._undo_reply(True)
        return {"restored": self.assistant.agent_context()["current_design"], "result": _result_summary(self.last_reply.result)}

    def get_missing_information(self) -> dict[str, Any]:
        return {"missing_information": self.assistant._missing_required_parameters()}

    def search_knowledge_base(self, query: str) -> dict[str, Any]:
        tokens = {
            token for token in query.casefold().replace("ß", "ss").replace("-", "_").split()
            if len(token) >= 3
        }
        entries = list(get_knowledge(query))
        refs = list(find_sources(query))
        for token in tokens:
            entries.extend(item for item in get_knowledge(token) if item not in entries)
            refs.extend(item for item in find_sources(token) if item not in refs)
        return {
            "query": query,
            "entries": [asdict(item) for item in entries],
            "sources": [asdict(item) for item in refs],
            "found": bool(entries or refs),
        }

    def explain_calculation(self, topic: str) -> dict[str, Any]:
        result = self.assistant.state.last_result
        if result is None:
            return {"available": False, "message": "No calculated result exists."}
        if "auswahl" in topic.casefold() or "variante" in topic.casefold():
            explanation = self.assistant._explain_selection()
        else:
            explanation = self.assistant._explain_governing()
        return {"available": True, "facts": explanation, "result": _result_summary(result)}


class LLMAgent:
    def __init__(self, assistant: Any, client: Any, model: str) -> None:
        self.assistant = assistant
        self.client = client
        self.model = model
        self.tools = EngineeringTools(assistant)

    def respond(self, user_text: str) -> Any:
        from ai.assistant import AssistantReply

        self.assistant.message_history.append({"role": "user", "content": user_text})
        context = json.dumps(self.assistant.agent_context(), ensure_ascii=False)
        messages = [*self.assistant.message_history[:-1], {
            "role": "user",
            "content": f"ENGINEERING_CONTEXT_JSON:\n{context}\n\nUSER_MESSAGE:\n{user_text}",
        }]
        response = self._request(messages, step="agent_turn")
        for _ in range(8):
            calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
            if not calls:
                text = response.output_text.strip()
                if not text:
                    raise RuntimeError("Das Sprachmodell lieferte keine Antwort.")
                self.assistant.message_history.append({"role": "assistant", "content": text})
                result = self.tools.last_reply.result if self.tools.last_reply else self.assistant.state.last_result
                return AssistantReply(text, result, True, self.assistant._recognized_parameters(result), self.assistant.state.last_recommendation or "")
            outputs = []
            for call in calls:
                try:
                    args = json.loads(call.arguments or "{}")
                    value = self.tools.dispatch(call.name, args)
                except Exception as exc:
                    LOGGER.exception("Agent tool failed model=%s tool=%s", self.model, call.name)
                    value = {"error": type(exc).__name__, "message": str(exc)}
                outputs.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(value, ensure_ascii=False, default=str)})
            response = self._request(outputs, step="tool_results", previous_response_id=response.id)
        raise RuntimeError("Die maximale Anzahl von Engineering-Toolschritten wurde erreicht.")

    def _request(self, input_data: Any, *, step: str, previous_response_id: str | None = None) -> Any:
        try:
            kwargs = {
                "model": self.model,
                "instructions": self.assistant.system_prompt + "\n\n" + (
                    "Du führst das Gespräch. Nutze Engineering-Tools für jede technische Zahl oder Normbewertung. "
                    "Erfinde nie Werte. Explizite Benutzerwerte sind USER_FIXED. Fachfragen ändern den State nicht. "
                    "Antworte nach Toolaufrufen natürlich und knapp auf Deutsch."
                ),
                "input": input_data,
                "tools": TOOL_DEFINITIONS,
            }
            if previous_response_id:
                kwargs["previous_response_id"] = previous_response_id
            return self.client.responses.create(**kwargs)
        except Exception as exc:
            request_id = getattr(exc, "request_id", None)
            LOGGER.exception("LLM request failed model=%s step=%s request_id=%s", self.model, step, request_id)
            raise RuntimeError(f"LLM-Aufruf fehlgeschlagen ({type(exc).__name__}, Modell {self.model}, Schritt {step}, Request-ID {request_id or 'nicht verfügbar'}): {exc}") from exc
