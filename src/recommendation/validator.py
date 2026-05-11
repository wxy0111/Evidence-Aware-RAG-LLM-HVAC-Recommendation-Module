import re
from typing import Optional
from .action_schema import ProposalSchema, ValidationResult


class ProposalValidator:
    def __init__(self, temp_min: float = 18.0, temp_max: float = 28.0, max_delta: float = 3.0):
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.max_delta = max_delta

    def validate(
        self,
        proposal: ProposalSchema,
        current_temp: Optional[float] = None,
        indoor_temp: Optional[float] = None,
        outdoor_temp: Optional[float] = None,
        expected_saving_percent: Optional[float] = None,
    ) -> ValidationResult:
        errors = []
        warnings = []

        if not (self.temp_min <= proposal.set_temperature_c <= self.temp_max):
            errors.append("temperature_out_of_bounds")

        if (proposal.set_temperature_c * 2) % 1 != 0:
            errors.append("temperature_not_on_half_degree_grid")

        if current_temp is not None and abs(proposal.set_temperature_c - current_temp) > self.max_delta:
            errors.append("temperature_step_too_large")

        if proposal.ac_switch not in {"on", "off"}:
            errors.append("invalid_ac_switch")

        if proposal.window_action not in {"open", "close", "ventilate"}:
            errors.append("invalid_window_action")

        if outdoor_temp is not None and indoor_temp is not None:
            if outdoor_temp > indoor_temp + 2 and proposal.window_action == "open":
                errors.append("unsafe_window_action_hot_outdoor")
            if outdoor_temp < indoor_temp - 5 and proposal.window_action == "open":
                errors.append("unsafe_window_action_cold_outdoor")

        if expected_saving_percent is not None:
            if abs(proposal.expected_saving_percent - expected_saving_percent) > 5.0:
                warnings.append("saving_percent_inconsistent")

        if len(proposal.message) > 90:
            warnings.append("message_too_long_for_notification")

        planning_json = proposal.metadata.get('planning_json', {}) if isinstance(proposal.metadata, dict) else {}
        if proposal.metadata.get('planning_stage_used') and isinstance(planning_json, dict):
            for required_key in ('action_clause', 'saving_clause', 'reason_clause'):
                if not str(planning_json.get(required_key, '')).strip():
                    warnings.append(f"planning_missing_{required_key}")

        msg = proposal.message or ""
        rounded_expected = int(round(proposal.expected_saving_percent))
        percent_matches = [int(x) for x in re.findall(r'約\s*(\d+)\s*%', msg)]
        if percent_matches and all(abs(x - rounded_expected) > 2 for x in percent_matches):
            warnings.append("message_saving_percent_mismatch")

        if f"{proposal.set_temperature_c:.1f}°C" not in msg and f"{proposal.set_temperature_c:.1f}℃" not in msg:
            if proposal.window_action != 'ventilate' or proposal.ac_switch != 'off':
                warnings.append("message_temperature_not_explicit")

        if proposal.ac_switch == 'off' and ('オフ' not in msg and '停止' not in msg):
            warnings.append("message_action_not_explicit_ac")
        if proposal.window_action == 'close' and ('窓を閉め' not in msg and '閉めて' not in msg):
            warnings.append("message_action_not_explicit_window")
        if proposal.window_action == 'ventilate' and ('換気' not in msg):
            warnings.append("message_action_not_explicit_ventilation")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def auto_repair(self, proposal: ProposalSchema) -> ValidationResult:
        warnings = []
        repaired_fields = {}
        original_message = proposal.message or proposal.short_message or ""
        message = original_message.strip()

        if not message:
            message = self._compose_fallback_message(proposal)
            repaired_fields['message'] = message
            warnings.append('message_filled_from_template')

        if not self._contains_temperature(message, proposal.set_temperature_c):
            message = self._append_sentence(message, f"設定温度は{proposal.set_temperature_c:.1f}°Cです")
            warnings.append('temperature_appended')

        if proposal.window_action == 'close' and ('窓を閉め' not in message and '閉めて' not in message):
            message = self._prepend_clause(message, '窓を閉め、')
            warnings.append('window_action_appended')
        elif proposal.window_action == 'ventilate' and '換気' not in message:
            message = self._append_sentence(message, '短時間の換気を含めた調整です')
            warnings.append('ventilation_action_appended')

        if proposal.ac_switch == 'off' and ('オフ' not in message and '停止' not in message):
            message = self._prepend_clause(message, 'エアコンをオフにし、')
            warnings.append('ac_action_appended')

        expected_percent_str = f"約{int(round(proposal.expected_saving_percent))}%"
        percent_matches = re.findall(r'約\s*\d+\s*%', message)
        if not percent_matches:
            message = self._append_sentence(message, f"{expected_percent_str}の節電が期待できます")
            warnings.append('saving_percent_appended')
        elif expected_percent_str not in message:
            message = re.sub(r'約\s*\d+\s*%', expected_percent_str, message, count=1)
            warnings.append('saving_percent_replaced')

        compact_message = self._compress_message(message)
        if compact_message != message:
            message = compact_message
            warnings.append('message_compressed')

        proposal.message = message
        if not proposal.short_message:
            proposal.short_message = message
        elif proposal.short_message != message and len(proposal.short_message) > len(message):
            proposal.short_message = message
        repaired_fields['message'] = proposal.message
        repaired_fields['short_message'] = proposal.short_message

        return ValidationResult(
            is_valid=True,
            errors=[],
            warnings=warnings,
            repaired=bool(warnings),
            repaired_fields=repaired_fields if warnings else None,
        )

    def _compose_fallback_message(self, proposal: ProposalSchema) -> str:
        if proposal.ac_switch == 'off' and proposal.window_action == 'ventilate':
            return f"エアコンをオフにし、短時間換気してください。約{int(round(proposal.expected_saving_percent))}%の節電が期待できます。"
        if proposal.window_action == 'close':
            return f"窓を閉め、設定温度を{proposal.set_temperature_c:.1f}°Cにしてください。約{int(round(proposal.expected_saving_percent))}%の節電が期待できます。"
        if proposal.window_action == 'ventilate':
            return f"設定温度を{proposal.set_temperature_c:.1f}°Cにし、短時間換気してください。約{int(round(proposal.expected_saving_percent))}%の節電が期待できます。"
        return f"設定温度を{proposal.set_temperature_c:.1f}°Cにしてください。約{int(round(proposal.expected_saving_percent))}%の節電が期待できます。"

    @staticmethod
    def _contains_temperature(message: str, temp: float) -> bool:
        return f"{temp:.1f}°C" in message or f"{temp:.1f}℃" in message

    @staticmethod
    def _append_sentence(message: str, sentence: str) -> str:
        message = message.strip()
        if not message:
            return sentence + '。'
        if not message.endswith('。'):
            message += '。'
        sentence = sentence.strip().rstrip('。')
        return message + sentence + '。'

    @staticmethod
    def _prepend_clause(message: str, clause: str) -> str:
        message = message.strip()
        if not message:
            return clause.rstrip('、') + '。'
        if message.startswith(clause):
            return message
        return clause + message

    @staticmethod
    def _compress_message(message: str, limit: int = 120) -> str:
        if len(message) <= limit:
            return message
        parts = [p.strip() for p in message.split('。') if p.strip()]
        if not parts:
            return message[:limit]
        compressed = parts[0] + '。'
        if len(compressed) <= limit:
            return compressed
        return compressed[:limit]
