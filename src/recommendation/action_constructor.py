from typing import List
from .action_schema import ProposalSchema


class ActionConstructor:
    def __init__(self, temp_min: float = 18.0, temp_max: float = 28.0, max_delta: float = 3.0):
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.max_delta = max_delta

    @staticmethod
    def _round_to_half(value: float) -> float:
        return round(value * 2.0) / 2.0

    def build(
        self,
        timestamp: str,
        current_temp: float,
        optimal_temp: float,
        indoor_temp: float,
        outdoor_temp: float,
        saving_percent: float,
    ) -> ProposalSchema:
        target = max(self.temp_min, min(self.temp_max, float(optimal_temp)))

        current_temp = float(current_temp)
        if abs(target - current_temp) > self.max_delta:
            if target > current_temp:
                target = current_temp + self.max_delta
            else:
                target = current_temp - self.max_delta

        target = self._round_to_half(float(target))

        # 二次保护，避免离散化后再次越界
        if abs(target - current_temp) > self.max_delta:
            if target > current_temp:
                target = self._round_to_half(current_temp + self.max_delta - 0.25)
            else:
                target = self._round_to_half(current_temp - self.max_delta + 0.25)

        ac_switch = "on" if abs(target - indoor_temp) >= 0.5 else "off"

        risk_flags: List[str] = []
        if outdoor_temp > indoor_temp + 2:
            window_action = "close"
            risk_flags.append("outdoor_too_hot_for_window_opening")
        elif outdoor_temp < indoor_temp - 5:
            window_action = "close"
            risk_flags.append("outdoor_too_cold_for_window_opening")
        elif abs(outdoor_temp - indoor_temp) <= 1.5:
            window_action = "ventilate"
        else:
            window_action = "close"

        if risk_flags:
            reason_type = "safety_priority"
        elif window_action == "close":
            reason_type = "indoor_stability"
        elif window_action == "ventilate":
            reason_type = "ventilation_balance"
        else:
            reason_type = "comfort_energy_balance"

        return ProposalSchema(
            timestamp=timestamp,
            set_temperature_c=float(target),
            ac_switch=ac_switch,
            window_action=window_action,
            expected_saving_percent=round(float(max(0.0, saving_percent)), 2),
            risk_flags=risk_flags,
            confidence=0.8,
            message="",
            short_message="",
            detailed_message="",
            reason_type=reason_type,
            message_style="planned_action_first",
            metadata={
                "content_planned": True,
                "reason_type": reason_type,
                "action_decided_by": "rule_based_action_constructor",
                "llm_role": "surface_realization_only",
            },
        )
