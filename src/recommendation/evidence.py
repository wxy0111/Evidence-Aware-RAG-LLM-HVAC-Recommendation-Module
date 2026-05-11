from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any


@dataclass
class EvidenceItem:
    evidence_id: str
    evidence_type: str
    evidence_level: int
    priority: int
    source: str
    content: str
    support_target: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidencePack:
    all_evidence: List[EvidenceItem]
    selected_evidence: List[EvidenceItem]
    discarded_evidence: List[EvidenceItem]
    rule_evidence: List[EvidenceItem]
    historical_evidence: List[EvidenceItem]
    safety_evidence: List[EvidenceItem]
    evidence_summary: str
    evidence_strength: str
    evidence_trace: Dict[str, Any]
