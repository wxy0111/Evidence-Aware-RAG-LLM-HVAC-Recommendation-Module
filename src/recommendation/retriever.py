import json
from pathlib import Path
from typing import List, Dict, Any

from .action_schema import ProposalSchema
from .paths import DEFAULT_KB_PATH


class KnowledgeRetriever:
    def __init__(self, kb_path: str | None = None):
        if kb_path is None:
            kb_path = str(DEFAULT_KB_PATH)
        self.kb_path = kb_path
        self.entries = self._load_entries()

    def _load_entries(self) -> List[Dict[str, Any]]:
        path = Path(self.kb_path)
        if not path.exists():
            return []
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []

    def retrieve(self, proposal: ProposalSchema, top_k: int = 3) -> List[Dict[str, Any]]:
        scored = []
        for entry in self.entries:
            score = self._score_entry(entry, proposal)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]

    def _score_entry(self, entry: Dict[str, Any], proposal: ProposalSchema) -> int:
        score = 0
        conditions = entry.get('conditions', {})

        reason_types = conditions.get('reason_type', [])
        if proposal.reason_type in reason_types:
            score += 3

        window_actions = conditions.get('window_action', [])
        if proposal.window_action in window_actions:
            score += 2

        ac_switches = conditions.get('ac_switch', [])
        if proposal.ac_switch in ac_switches:
            score += 1

        risk_flags = conditions.get('risk_flags', [])
        if any(flag in proposal.risk_flags for flag in risk_flags):
            score += 4

        return score

    @staticmethod
    def format_context(entries: List[Dict[str, Any]]) -> str:
        if not entries:
            return '関連知識なし'
        lines = []
        for i, entry in enumerate(entries, 1):
            title = entry.get('title', f'knowledge_{i}')
            guidance = entry.get('guidance', '')
            lines.append(f'{i}. {title}: {guidance}')
        return '\n'.join(lines)
