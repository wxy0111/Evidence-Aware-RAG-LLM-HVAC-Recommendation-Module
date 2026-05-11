from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from .feedback_retriever import UserFeedbackCase


@dataclass
class UserPreferenceProfile:
    count: int = 0
    accepted_rate: float = 0.0
    prefers_brief: bool = False
    prefers_reasoning: bool = False
    prefers_soft_tone: bool = True
    prefers_numeric_saving: bool = True
    prefers_history_reference: bool = False
    prefers_gradual_adjustment: bool = True
    accepts_window_action: bool = True
    accepts_ac_off_strategy: bool = True
    avg_max_acceptable_temp_step: float = 1.0
    top_preference_tags: List[str] | None = None
    top_feedback_categories: List[str] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_prompt_text(self) -> str:
        tags = ', '.join(self.top_preference_tags or []) or 'none'
        cats = ', '.join(self.top_feedback_categories or []) or 'none'
        return (
            f"user_profile: count={self.count}, accepted_rate={self.accepted_rate:.2f}, "
            f"prefers_brief={self.prefers_brief}, prefers_reasoning={self.prefers_reasoning}, "
            f"prefers_soft_tone={self.prefers_soft_tone}, prefers_numeric_saving={self.prefers_numeric_saving}, "
            f"prefers_history_reference={self.prefers_history_reference}, "
            f"prefers_gradual_adjustment={self.prefers_gradual_adjustment}, "
            f"accepts_window_action={self.accepts_window_action}, accepts_ac_off_strategy={self.accepts_ac_off_strategy}, "
            f"avg_max_acceptable_temp_step={self.avg_max_acceptable_temp_step:.2f}, "
            f"top_preference_tags={tags}, top_feedback_categories={cats}"
        )


class UserProfileBuilder:
    def build(self, cases: List[UserFeedbackCase]) -> UserPreferenceProfile:
        if not cases:
            return UserPreferenceProfile()

        n = len(cases)
        accepted = sum(1 for c in cases if c.accepted)
        prefers_brief = sum(1 for c in cases if c.prefers_brief_message) >= (n / 2)
        prefers_reasoning = sum(1 for c in cases if c.prefers_reasoning) >= (n / 2)
        prefers_soft_tone = sum(1 for c in cases if c.prefers_soft_tone) >= (n / 2)
        prefers_numeric_saving = sum(1 for c in cases if c.prefers_numeric_saving) >= (n / 2)
        prefers_history_reference = sum(1 for c in cases if c.prefers_history_reference) >= (n / 2)
        prefers_gradual_adjustment = sum(1 for c in cases if c.prefers_gradual_adjustment) >= (n / 2)
        accepts_window_action = sum(1 for c in cases if c.accepts_window_action) >= (n / 2)
        accepts_ac_off_strategy = sum(1 for c in cases if c.accepts_ac_off_strategy) >= (n / 2)
        avg_max_step = sum(float(c.max_acceptable_temp_step) for c in cases) / n

        def top_values(values: List[str], limit: int = 3) -> List[str]:
            counts: Dict[str, int] = {}
            for value in values:
                v = str(value).strip()
                if not v:
                    continue
                counts[v] = counts.get(v, 0) + 1
            return [k for k, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]]

        return UserPreferenceProfile(
            count=n,
            accepted_rate=accepted / n,
            prefers_brief=prefers_brief,
            prefers_reasoning=prefers_reasoning,
            prefers_soft_tone=prefers_soft_tone,
            prefers_numeric_saving=prefers_numeric_saving,
            prefers_history_reference=prefers_history_reference,
            prefers_gradual_adjustment=prefers_gradual_adjustment,
            accepts_window_action=accepts_window_action,
            accepts_ac_off_strategy=accepts_ac_off_strategy,
            avg_max_acceptable_temp_step=avg_max_step,
            top_preference_tags=top_values([c.preference_tag for c in cases]),
            top_feedback_categories=top_values([c.feedback_category for c in cases]),
        )
