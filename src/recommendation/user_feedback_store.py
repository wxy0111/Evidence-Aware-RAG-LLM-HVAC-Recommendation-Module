import csv
from datetime import datetime
from pathlib import Path

from .paths import DEFAULT_FEEDBACK_PATH


class UserFeedbackStore:
    HEADER = [
        'timestamp',
        'feedback_category',
        'feedback_type',
        'preference_tag',
        'context_note',
        'accepted',
        'executed',
        'partially_executed',
        'rejection_reason',
        'temp_setpoint_c',
        'window_action',
        'ac_switch',
        'reason_hint',
        'thermal_preference',
        'humidity_preference',
        'ventilation_comfort',
        'noise_sensitivity',
        'prefers_brief_message',
        'prefers_reasoning',
        'prefers_soft_tone',
        'prefers_numeric_saving',
        'prefers_history_reference',
        'max_acceptable_temp_step',
        'prefers_gradual_adjustment',
        'accepts_window_action',
        'accepts_ac_off_strategy',
        'time_of_day_preference',
        'activity_context_preference',
        'seasonal_preference',
        'environmental_constraint_preference',
    ]

    def __init__(self, csv_path: str | None = None):
        if csv_path is None:
            csv_path = str(DEFAULT_FEEDBACK_PATH)
        self.csv_path = Path(csv_path)
        self._ensure_file()

    def _ensure_file(self):
        if self.csv_path.exists():
            return
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.csv_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.HEADER)

    def append_feedback(
        self,
        feedback_category: str,
        feedback_type: str,
        preference_tag: str,
        context_note: str,
        accepted: bool,
        executed: bool,
        partially_executed: bool,
        rejection_reason: str,
        temp_setpoint_c: float,
        window_action: str,
        ac_switch: str,
        reason_hint: str,
        thermal_preference: str = 'neutral',
        humidity_preference: str = 'neutral',
        ventilation_comfort: str = 'neutral',
        noise_sensitivity: str = 'medium',
        prefers_brief_message: bool = False,
        prefers_reasoning: bool = True,
        prefers_soft_tone: bool = True,
        prefers_numeric_saving: bool = True,
        prefers_history_reference: bool = False,
        max_acceptable_temp_step: float = 1.0,
        prefers_gradual_adjustment: bool = True,
        accepts_window_action: bool = True,
        accepts_ac_off_strategy: bool = True,
        time_of_day_preference: str = 'all',
        activity_context_preference: str = 'work',
        seasonal_preference: str = 'all',
        environmental_constraint_preference: str = 'none',
        timestamp: str | None = None,
    ):
        ts = timestamp or datetime.now().isoformat(timespec='seconds')
        with open(self.csv_path, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                ts,
                feedback_category,
                feedback_type,
                preference_tag,
                context_note,
                int(bool(accepted)),
                int(bool(executed)),
                int(bool(partially_executed)),
                rejection_reason,
                temp_setpoint_c,
                window_action,
                ac_switch,
                reason_hint,
                thermal_preference,
                humidity_preference,
                ventilation_comfort,
                noise_sensitivity,
                int(bool(prefers_brief_message)),
                int(bool(prefers_reasoning)),
                int(bool(prefers_soft_tone)),
                int(bool(prefers_numeric_saving)),
                int(bool(prefers_history_reference)),
                max_acceptable_temp_step,
                int(bool(prefers_gradual_adjustment)),
                int(bool(accepts_window_action)),
                int(bool(accepts_ac_off_strategy)),
                time_of_day_preference,
                activity_context_preference,
                seasonal_preference,
                environmental_constraint_preference,
            ])
