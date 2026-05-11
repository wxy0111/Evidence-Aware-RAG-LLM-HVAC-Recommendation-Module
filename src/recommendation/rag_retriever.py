from __future__ import annotations

import csv
import json
import math
import os
import shlex
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import openai

from .action_schema import ProposalSchema
from .paths import DEFAULT_HISTORY_PATH, DEFAULT_KB_PATH


@dataclass
class RetrievedChunk:
    chunk_id: str
    chunk_type: str
    text: str
    metadata: Dict[str, Any]
    lexical_score: float
    semantic_score: float
    hybrid_score: float


class _EmbeddingClient:
    def __init__(self, model: str = 'text-embedding-3-small'):
        self.model = model
        self.client = None
        api_key = self._load_openai_api_key()
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)

    @staticmethod
    def _load_openai_api_key() -> str:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            return api_key
        zshrc_path = os.path.expanduser('~/.zshrc')
        if not os.path.exists(zshrc_path):
            return ''
        try:
            with open(zshrc_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith('export OPENAI_API_KEY='):
                        continue
                    _, value = line.split('=', 1)
                    value = shlex.split(value.strip())
                    return value[0] if value else ''
        except OSError:
            return ''
        return ''

    def available(self) -> bool:
        return self.client is not None

    def embed(self, text: str) -> List[float]:
        if not self.client:
            return self._fallback_embed(text)
        try:
            resp = self.client.embeddings.create(model=self.model, input=text)
            return list(resp.data[0].embedding)
        except Exception:
            return self._fallback_embed(text)

    @staticmethod
    def _fallback_embed(text: str, dims: int = 64) -> List[float]:
        vec = [0.0] * dims
        for token in text.lower().replace('、', ' ').replace('。', ' ').split():
            idx = hash(token) % dims
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class HybridRAGRetriever:
    def __init__(
        self,
        kb_path: str | None = None,
        history_path: str | None = None,
        embedding_model: str = 'text-embedding-3-small',
    ):
        self.kb_path = kb_path or str(DEFAULT_KB_PATH)
        self.history_path = history_path or str(DEFAULT_HISTORY_PATH)
        self.embedding_client = _EmbeddingClient(model=embedding_model)
        self.rule_chunks = self._load_rule_chunks()
        self.history_chunks = self._load_history_chunks()

    def retrieve(
        self,
        proposal: ProposalSchema,
        top_k_rules: int = 3,
        top_k_history: int = 5,
        exclude_history_timestamps: List[str] | None = None,
    ) -> Dict[str, List[RetrievedChunk]]:
        query_text = self._proposal_to_query_text(proposal)
        query_emb = self.embedding_client.embed(query_text)

        rule_chunks = self._rank_chunks(query_emb, proposal, self.rule_chunks, top_k_rules)
        history_source = self._filter_history_chunks(exclude_history_timestamps or [])
        history_chunks = self._rank_chunks(query_emb, proposal, history_source, top_k_history)
        return {
            'query_text': query_text,
            'rules': rule_chunks,
            'history': history_chunks,
        }

    def _load_rule_chunks(self) -> List[Dict[str, Any]]:
        path = Path(self.kb_path)
        if not path.exists():
            return []
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        chunks = []
        for i, entry in enumerate(data if isinstance(data, list) else [], 1):
            text = self._rule_entry_to_text(entry)
            chunks.append({
                'chunk_id': str(entry.get('id', f'rule_{i}')),
                'chunk_type': 'rule',
                'text': text,
                'metadata': entry,
                'embedding': self.embedding_client.embed(text),
            })
        return chunks

    def _load_history_chunks(self) -> List[Dict[str, Any]]:
        path = Path(self.history_path)
        if not path.exists():
            return []
        rows = []
        with open(path, 'r', encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        chunks = []
        for i, row in enumerate(rows, 1):
            text = self._history_row_to_text(row)
            chunks.append({
                'chunk_id': f"hist_{row.get('timestamp', i)}_{i}",
                'chunk_type': 'history',
                'text': text,
                'metadata': row,
                'embedding': self.embedding_client.embed(text),
            })
        return chunks

    def _filter_history_chunks(self, exclude_history_timestamps: List[str]) -> List[Dict[str, Any]]:
        if not exclude_history_timestamps:
            return self.history_chunks
        excluded = {str(x).strip() for x in exclude_history_timestamps if str(x).strip()}
        filtered = []
        for chunk in self.history_chunks:
            ts = str(chunk.get('metadata', {}).get('timestamp', '')).strip()
            ts_alt = ts.replace(' ', 'T') if ts else ''
            if ts in excluded or ts_alt in excluded:
                continue
            filtered.append(chunk)
        return filtered

    def _rank_chunks(self, query_emb: List[float], proposal: ProposalSchema, chunks: List[Dict[str, Any]], top_k: int) -> List[RetrievedChunk]:
        scored: List[RetrievedChunk] = []
        for chunk in chunks:
            semantic = self._cosine(query_emb, chunk['embedding'])
            lexical = self._lexical_score(proposal, chunk)
            hybrid = 0.45 * lexical + 0.55 * semantic
            min_threshold = 0.02 if chunk['chunk_type'] == 'history' else 0.0
            if hybrid <= min_threshold:
                continue
            scored.append(RetrievedChunk(
                chunk_id=chunk['chunk_id'],
                chunk_type=chunk['chunk_type'],
                text=chunk['text'],
                metadata=chunk['metadata'],
                lexical_score=lexical,
                semantic_score=semantic,
                hybrid_score=hybrid,
            ))
        scored.sort(key=lambda x: x.hybrid_score, reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2:
            return 0.0
        n = min(len(v1), len(v2))
        dot = sum(v1[i] * v2[i] for i in range(n))
        norm1 = math.sqrt(sum(v * v for v in v1[:n])) or 1.0
        norm2 = math.sqrt(sum(v * v for v in v2[:n])) or 1.0
        return dot / (norm1 * norm2)

    def _lexical_score(self, proposal: ProposalSchema, chunk: Dict[str, Any]) -> float:
        metadata = chunk.get('metadata', {})
        if chunk['chunk_type'] == 'rule':
            conditions = metadata.get('conditions', {})
            score = 0.0
            if proposal.reason_type in conditions.get('reason_type', []):
                score += 1.0
            if proposal.window_action in conditions.get('window_action', []):
                score += 0.8
            if proposal.ac_switch in conditions.get('ac_switch', []):
                score += 0.4
            risk_flags = conditions.get('risk_flags', [])
            if any(flag in proposal.risk_flags for flag in risk_flags):
                score += 1.2
            return score

        try:
            ts = str(proposal.timestamp).replace('Z', '')
            target_dt = datetime.fromisoformat(ts.replace(' ', 'T'))
            target_hour = target_dt.hour
        except Exception:
            target_hour = 12
        target_indoor = float(proposal.metadata.get('indoor_temp', proposal.set_temperature_c))
        target_outdoor = float(proposal.metadata.get('outdoor_temp', proposal.set_temperature_c))
        target_set = float(proposal.set_temperature_c)
        target_save = float(proposal.expected_saving_percent)
        try:
            row_ts = str(metadata.get('timestamp', '')).replace(' ', 'T')
            row_hour = datetime.fromisoformat(row_ts).hour
        except Exception:
            row_hour = target_hour
        indoor = self._to_float(metadata.get('indoor_temp', metadata.get('current_temp', target_indoor)), target_indoor)
        outdoor = self._to_float(metadata.get('outdoor_temp', target_outdoor), target_outdoor)
        optimal = self._to_float(metadata.get('optimal_temp', target_set), target_set)
        original_pred = self._to_float(metadata.get('original_predicted_energy', 0.0), 0.0)
        optimized_energy = self._to_float(metadata.get('optimized_energy', 0.0), 0.0)
        if original_pred > 0:
            saving = max(0.0, (original_pred - optimized_energy) / original_pred * 100.0)
        else:
            saving = target_save
        score = 1.0
        score -= abs(row_hour - target_hour) * 0.05
        score -= abs(indoor - target_indoor) * 0.08
        score -= abs(outdoor - target_outdoor) * 0.06
        score -= abs(optimal - target_set) * 0.10
        score -= abs(saving - target_save) * 0.02
        return max(0.0, score)

    @staticmethod
    def _to_float(value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default

    @staticmethod
    def _rule_entry_to_text(entry: Dict[str, Any]) -> str:
        title = str(entry.get('title', 'rule'))
        category = str(entry.get('category', 'general'))
        guidance = str(entry.get('guidance', ''))
        conditions = entry.get('conditions', {}) or {}
        return (
            f"規則タイトル: {title}\n"
            f"カテゴリ: {category}\n"
            f"適用条件: reason_type={conditions.get('reason_type', [])}, "
            f"window_action={conditions.get('window_action', [])}, ac_switch={conditions.get('ac_switch', [])}, risk_flags={conditions.get('risk_flags', [])}\n"
            f"ガイダンス: {guidance}"
        )

    @staticmethod
    def _history_row_to_text(row: Dict[str, Any]) -> str:
        indoor = row.get('indoor_temp', row.get('current_temp', '-'))
        outdoor = row.get('outdoor_temp', '-')
        optimal = row.get('optimal_temp', '-')
        original_pred = HybridRAGRetriever._to_float(row.get('original_predicted_energy', 0.0), 0.0)
        optimized_energy = HybridRAGRetriever._to_float(row.get('optimized_energy', 0.0), 0.0)
        if original_pred > 0:
            saving = max(0.0, (original_pred - optimized_energy) / original_pred * 100.0)
        else:
            saving = 0.0
        return (
            f"履歴時刻: {row.get('timestamp', '')}\n"
            f"室内温度: {indoor}°C, 室外温度: {outdoor}°C\n"
            f"推奨設定温度: {optimal}°C\n"
            f"このケースの推定節電率: {saving:.1f}%\n"
            f"optimization_type: {row.get('optimization_type', '')}"
        )

    @staticmethod
    def _proposal_to_query_text(proposal: ProposalSchema) -> str:
        indoor = proposal.metadata.get('indoor_temp', 'unknown')
        outdoor = proposal.metadata.get('outdoor_temp', 'unknown')
        risks = ', '.join(proposal.risk_flags) if proposal.risk_flags else 'なし'
        return (
            f"現在の空調推薦条件。reason_type は {proposal.reason_type}。"
            f"ac_switch は {proposal.ac_switch}、window_action は {proposal.window_action}。"
            f"推奨温度は {proposal.set_temperature_c:.1f}°C。期待節電率は {proposal.expected_saving_percent:.1f}% 。"
            f"室内温度は {indoor}°C、室外温度は {outdoor}°C。"
            f"risk_flags は {risks}。"
            f"この条件に意味的に近い規則知識と過去事例を探したい。"
        )
