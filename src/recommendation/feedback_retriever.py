import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .action_schema import ProposalSchema
from .paths import DEFAULT_FEEDBACK_PATH


@dataclass
class UserFeedbackCase:
    timestamp: str
    feedback_category: str
    feedback_type: str
    preference_tag: str
    context_note: str
    accepted: bool
    executed: bool
    partially_executed: bool
    rejection_reason: str
    temp_setpoint_c: float
    window_action: str
    ac_switch: str
    reason_hint: str
    thermal_preference: str
    humidity_preference: str
    ventilation_comfort: str
    noise_sensitivity: str
    prefers_brief_message: bool
    prefers_reasoning: bool
    prefers_soft_tone: bool
    prefers_numeric_saving: bool
    prefers_history_reference: bool
    max_acceptable_temp_step: float
    prefers_gradual_adjustment: bool
    accepts_window_action: bool
    accepts_ac_off_strategy: bool
    time_of_day_preference: str
    activity_context_preference: str
    seasonal_preference: str
    environmental_constraint_preference: str
    score: float


class UserFeedbackRetriever:
    def __init__(self, csv_path: str | None = None):
        if csv_path is None:
            csv_path = str(DEFAULT_FEEDBACK_PATH)
        self.csv_path = csv_path
        self.rows = self._load_rows()

    def _load_rows(self) -> List[Dict[str, Any]]:
        path = Path(self.csv_path)
        if not path.exists():
            return []
        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))

    def retrieve(self, proposal: ProposalSchema, top_k: int = 3) -> List[UserFeedbackCase]:
        if not self.rows:
            return []

        try:
            target_dt = datetime.fromisoformat(str(proposal.timestamp).replace('Z', '').replace(' ', 'T'))
            target_hour = target_dt.hour
        except Exception:
            target_hour = 12

        target_temp = float(proposal.set_temperature_c)
        scored: List[UserFeedbackCase] = []

        for row in self.rows:
            try:
                row_dt = datetime.fromisoformat(str(row.get('timestamp', '')).replace('Z', '').replace(' ', 'T'))
                hour_gap = abs(row_dt.hour - target_hour)
            except Exception:
                hour_gap = 6

            row_temp = self._to_float(row.get('temp_setpoint_c', target_temp), target_temp)
            temp_gap = abs(row_temp - target_temp)
            accepted = self._to_bool(row.get('accepted', '0'))
            executed = self._to_bool(row.get('executed', '0'))
            partially_executed = self._to_bool(row.get('partially_executed', '0'))
            prefers_reasoning = self._to_bool(row.get('prefers_reasoning', '0'))
            prefers_brief_message = self._to_bool(row.get('prefers_brief_message', '0'))
            prefers_soft_tone = self._to_bool(row.get('prefers_soft_tone', '0'))
            prefers_numeric_saving = self._to_bool(row.get('prefers_numeric_saving', '0'))
            prefers_history_reference = self._to_bool(row.get('prefers_history_reference', '0'))
            prefers_gradual_adjustment = self._to_bool(row.get('prefers_gradual_adjustment', '0'))
            accepts_window_action = self._to_bool(row.get('accepts_window_action', '1'))
            accepts_ac_off_strategy = self._to_bool(row.get('accepts_ac_off_strategy', '1'))
            window_match = 0 if str(row.get('window_action', '')).strip() == proposal.window_action else 1
            ac_match = 0 if str(row.get('ac_switch', '')).strip() == proposal.ac_switch else 1
            max_step = self._to_float(row.get('max_acceptable_temp_step', 1.0), 1.0)

            score = hour_gap * 1.0 + temp_gap * 2.0 + window_match * 1.5 + ac_match * 1.0
            if accepted:
                score -= 0.5
            if executed:
                score -= 0.3
            if prefers_gradual_adjustment and abs(target_temp - row_temp) <= max_step:
                score -= 0.3

            scored.append(UserFeedbackCase(
                timestamp=str(row.get('timestamp', '')),
                feedback_category=str(row.get('feedback_category', '')),
                feedback_type=str(row.get('feedback_type', '')),
                preference_tag=str(row.get('preference_tag', '')),
                context_note=str(row.get('context_note', '')),
                accepted=accepted,
                executed=executed,
                partially_executed=partially_executed,
                rejection_reason=str(row.get('rejection_reason', '')),
                temp_setpoint_c=row_temp,
                window_action=str(row.get('window_action', '')),
                ac_switch=str(row.get('ac_switch', '')),
                reason_hint=str(row.get('reason_hint', '')),
                thermal_preference=str(row.get('thermal_preference', '')),
                humidity_preference=str(row.get('humidity_preference', '')),
                ventilation_comfort=str(row.get('ventilation_comfort', '')),
                noise_sensitivity=str(row.get('noise_sensitivity', '')),
                prefers_brief_message=prefers_brief_message,
                prefers_reasoning=prefers_reasoning,
                prefers_soft_tone=prefers_soft_tone,
                prefers_numeric_saving=prefers_numeric_saving,
                prefers_history_reference=prefers_history_reference,
                max_acceptable_temp_step=max_step,
                prefers_gradual_adjustment=prefers_gradual_adjustment,
                accepts_window_action=accepts_window_action,
                accepts_ac_off_strategy=accepts_ac_off_strategy,
                time_of_day_preference=str(row.get('time_of_day_preference', '')),
                activity_context_preference=str(row.get('activity_context_preference', '')),
                seasonal_preference=str(row.get('seasonal_preference', '')),
                environmental_constraint_preference=str(row.get('environmental_constraint_preference', '')),
                score=score,
            ))

        scored.sort(key=lambda x: x.score)
        return scored[:top_k]

    @staticmethod
    def summarize(cases: List[UserFeedbackCase]) -> Dict[str, Any]:
        if not cases:
            return {
                'count': 0,
                'accepted_count': 0,
                'accepted_rate': 0.0,
                'preference_tags': [],
                'feedback_categories': [],
                'prefers_reasoning_rate': 0.0,
                'prefers_brief_rate': 0.0,
                'prefers_soft_tone_rate': 0.0,
            }

        accepted_count = sum(1 for c in cases if c.accepted)
        tags = [c.preference_tag for c in cases if c.preference_tag]
        categories = [c.feedback_category for c in cases if c.feedback_category]
        return {
            'count': len(cases),
            'accepted_count': accepted_count,
            'accepted_rate': accepted_count / len(cases),
            'preference_tags': tags,
            'feedback_categories': categories,
            'prefers_reasoning_rate': sum(1 for c in cases if c.prefers_reasoning) / len(cases),
            'prefers_brief_rate': sum(1 for c in cases if c.prefers_brief_message) / len(cases),
            'prefers_soft_tone_rate': sum(1 for c in cases if c.prefers_soft_tone) / len(cases),
        }

    @staticmethod
    def format_context(cases: List[UserFeedbackCase]) -> str:
        if not cases:
            return '関連するユーザーフィードバックなし'
        lines = []
        for i, c in enumerate(cases, 1):
            lines.append(
                f"{i}. {c.timestamp} / category={c.feedback_category} / tag={c.preference_tag} / accepted={c.accepted} / thermal={c.thermal_preference} / brief={c.prefers_brief_message} / reasoning={c.prefers_reasoning} / note={c.context_note} / hint={c.reason_hint}"
            )
        return '\n'.join(lines)

    @staticmethod
    def _to_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _to_bool(value: Any) -> bool:
        return str(value).strip().lower() in {'1', 'true', 'yes', 'y'}
