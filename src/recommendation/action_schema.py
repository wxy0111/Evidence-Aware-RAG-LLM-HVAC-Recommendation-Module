from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class ProposalSchema:
    timestamp: str
    set_temperature_c: float
    ac_switch: str
    window_action: str
    expected_saving_percent: float
    risk_flags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    message: str = ""
    short_message: str = ""
    detailed_message: str = ""
    reason_type: str = ""
    message_style: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    repaired: bool = False
    repaired_fields: Optional[Dict[str, Any]] = None
