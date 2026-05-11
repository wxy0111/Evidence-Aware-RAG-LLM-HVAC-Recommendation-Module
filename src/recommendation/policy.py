from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple


@dataclass
class PolicyConfig:
    min_saving_percent: float = 2.0
    min_temp_delta: float = 0.5
    cooldown_minutes: int = 60
    working_hours_only: bool = True


class RecommendationPolicy:
    def __init__(self, config: Optional[PolicyConfig] = None):
        self.config = config or PolicyConfig()

    def should_trigger(
        self,
        timestamp: datetime,
        is_working_hour: bool,
        current_temp: float,
        optimal_temp: float,
        saving_percent: float,
        last_proposal_time: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        if self.config.working_hours_only and not is_working_hour:
            return False, "non_working_hour"

        if saving_percent < self.config.min_saving_percent:
            return False, "saving_below_threshold"

        if abs(optimal_temp - current_temp) < self.config.min_temp_delta:
            return False, "temperature_change_too_small"

        if last_proposal_time is not None:
            delta_minutes = (timestamp - last_proposal_time).total_seconds() / 60.0
            if delta_minutes < self.config.cooldown_minutes:
                return False, "cooldown_active"

        return True, "triggered"
