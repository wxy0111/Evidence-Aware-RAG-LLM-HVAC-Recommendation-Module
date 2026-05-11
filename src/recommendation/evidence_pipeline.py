from __future__ import annotations

from typing import List, Dict, Any

from .action_schema import ProposalSchema
from .evidence import EvidenceItem, EvidencePack
from .retriever import KnowledgeRetriever
from .history_retriever import HistoricalCaseRetriever
from .feedback_retriever import UserFeedbackRetriever
from .rag_retriever import HybridRAGRetriever
from .user_profile import UserProfileBuilder


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _history_expected_saving(case: Dict[str, Any]) -> float:
    original_pred = _to_float(case.get('original_predicted_energy', 0.0), 0.0)
    optimized_energy = _to_float(case.get('optimized_energy', 0.0), 0.0)
    if original_pred > 0:
        return max(0.0, (original_pred - optimized_energy) / original_pred * 100.0)
    return 0.0


class EvidenceCollector:
    def __init__(self):
        self.knowledge_retriever = KnowledgeRetriever()
        self.history_retriever = HistoricalCaseRetriever()
        self.feedback_retriever = UserFeedbackRetriever()
        self.rag_retriever = HybridRAGRetriever()
        self.user_profile_builder = UserProfileBuilder()

    def collect(self, proposal: ProposalSchema) -> List[EvidenceItem]:
        items: List[EvidenceItem] = []

        exclude_timestamps = []
        current_timestamp = str(proposal.timestamp or '').strip()
        if current_timestamp:
            exclude_timestamps.append(current_timestamp)
            exclude_timestamps.append(current_timestamp.replace('T', ' '))
        rag_result = self.rag_retriever.retrieve(
            proposal,
            top_k_rules=5,
            top_k_history=5,
            exclude_history_timestamps=exclude_timestamps,
        )
        proposal.metadata['rag_query_text'] = rag_result.get('query_text', '')

        for chunk in rag_result.get('rules', []):
            entry = chunk.metadata
            category = str(entry.get('category', 'rule'))
            is_safety = 'safety' in category or proposal.reason_type == 'safety_priority'
            items.append(EvidenceItem(
                evidence_id=str(chunk.chunk_id),
                evidence_type='rule',
                evidence_level=1 if not is_safety else 4,
                priority=100 if is_safety else 70,
                source='recommendation_knowledge_base.json',
                content=str(chunk.text),
                support_target=category,
                score=float(chunk.hybrid_score * 100.0),
                metadata={
                    'title': entry.get('title', ''),
                    'category': category,
                    'conditions': entry.get('conditions', {}),
                    'lexical_score': chunk.lexical_score,
                    'semantic_score': chunk.semantic_score,
                    'hybrid_score': chunk.hybrid_score,
                    'retrieval_mode': 'hybrid_rag',
                }
            ))

        for chunk in rag_result.get('history', []):
            case = chunk.metadata
            items.append(EvidenceItem(
                evidence_id=str(chunk.chunk_id),
                evidence_type='historical_case',
                evidence_level=2,
                priority=60,
                source='optimization_results.csv',
                content=str(chunk.text),
                support_target='historical_performance',
                score=float(chunk.hybrid_score * 100.0),
                metadata={
                    'timestamp': case.get('timestamp', ''),
                    'hour': case.get('hour', ''),
                    'indoor_temp': case.get('indoor_temp', case.get('current_temp', '')),
                    'outdoor_temp': case.get('outdoor_temp', ''),
                    'optimal_temp': case.get('optimal_temp', ''),
                    'expected_saving_percent': _history_expected_saving(case),
                    'optimization_type': case.get('optimization_type', ''),
                    'lexical_score': chunk.lexical_score,
                    'semantic_score': chunk.semantic_score,
                    'hybrid_score': chunk.hybrid_score,
                    'retrieval_mode': 'hybrid_rag',
                }
            ))

        feedback_cases = self.feedback_retriever.retrieve(proposal, top_k=3)
        feedback_summary = self.feedback_retriever.summarize(feedback_cases)
        user_profile = self.user_profile_builder.build(feedback_cases)
        proposal.metadata['retrieved_feedback_count'] = feedback_summary['count']
        proposal.metadata['feedback_acceptance_rate'] = feedback_summary['accepted_rate']
        proposal.metadata['feedback_preference_tags'] = feedback_summary['preference_tags']
        proposal.metadata['user_preference_profile'] = user_profile.to_dict()
        proposal.metadata['user_preference_profile_text'] = user_profile.to_prompt_text()
        for idx, case in enumerate(feedback_cases, 1):
            items.append(EvidenceItem(
                evidence_id=f"feedback_{idx}_{case.timestamp}",
                evidence_type='user_feedback',
                evidence_level=3,
                priority=85 if case.accepted else 50,
                source='user_feedback_examples.csv',
                content=(
                    f"User feedback at {case.timestamp}: tag={case.preference_tag}, accepted={case.accepted}, "
                    f"note={case.context_note}, hint={case.reason_hint}"
                ),
                support_target='user_preference',
                score=max(0.0, 100.0 - case.score * 10.0),
                metadata={
                    'feedback_type': case.feedback_type,
                    'preference_tag': case.preference_tag,
                    'accepted': case.accepted,
                    'context_note': case.context_note,
                    'reason_hint': case.reason_hint,
                    'temp_setpoint_c': case.temp_setpoint_c,
                    'window_action': case.window_action,
                    'ac_switch': case.ac_switch,
                    'retrieval_mode': 'feedback_case_matching',
                }
            ))

        return items


class EvidenceSelector:
    def __init__(self, max_selected: int = 5):
        self.max_selected = max_selected

    def select(self, proposal: ProposalSchema, items: List[EvidenceItem]) -> EvidencePack:
        sorted_items = sorted(
            items,
            key=lambda x: (x.priority, x.score),
            reverse=True,
        )

        selected: List[EvidenceItem] = []
        discarded: List[EvidenceItem] = []
        picked_types: Dict[str, int] = {'rule': 0, 'historical_case': 0, 'user_feedback': 0}

        history_candidates = [x for x in sorted_items if x.evidence_type == 'historical_case']

        for item in sorted_items:
            # keep balance between rules and history while prioritizing safety
            if item.evidence_type == 'rule' and picked_types['rule'] >= 2 and item.priority < 100:
                discarded.append(item)
                continue
            if item.evidence_type == 'historical_case' and picked_types['historical_case'] >= 2:
                discarded.append(item)
                continue
            if item.evidence_type == 'user_feedback' and picked_types['user_feedback'] >= 1:
                discarded.append(item)
                continue
            selected.append(item)
            picked_types[item.evidence_type] += 1
            if len(selected) >= self.max_selected:
                break

        if history_candidates and picked_types['historical_case'] == 0:
            best_history = history_candidates[0]
            non_safety_rules = [x for x in selected if x.evidence_type == 'rule' and x.priority < 100]
            if len(selected) < self.max_selected:
                selected.append(best_history)
                picked_types['historical_case'] += 1
            elif non_safety_rules:
                replace_target = non_safety_rules[-1]
                selected = [best_history if x.evidence_id == replace_target.evidence_id else x for x in selected]
                picked_types['historical_case'] += 1
                picked_types['rule'] = max(0, picked_types['rule'] - 1)

        # Prefer a fuller pack: safety rule + one history + one feedback + up to two rules
        if history_candidates and picked_types['historical_case'] < 1:
            for candidate in history_candidates:
                if all(candidate.evidence_id != x.evidence_id for x in selected):
                    if len(selected) < self.max_selected:
                        selected.append(candidate)
                        picked_types['historical_case'] += 1
                    break

        selected_ids = {id(x) for x in selected}
        for item in sorted_items:
            if id(item) not in selected_ids and item not in discarded:
                discarded.append(item)

        rule_evidence = [x for x in selected if x.evidence_type == 'rule']
        historical_evidence = [x for x in selected if x.evidence_type == 'historical_case']
        feedback_evidence = [x for x in selected if x.evidence_type == 'user_feedback']
        safety_evidence = [x for x in selected if x.priority >= 100 or x.evidence_level == 4]

        summary = EvidenceSummarizer().summarize(selected)
        strength = self._estimate_strength(selected)
        trace = {
            'retrieved_count': len(items),
            'selected_count': len(selected),
            'discarded_count': len(discarded),
            'selected_ids': [x.evidence_id for x in selected],
            'selected_rule_ids': [x.evidence_id for x in rule_evidence],
            'selected_history_ids': [x.evidence_id for x in historical_evidence],
            'selected_feedback_ids': [x.evidence_id for x in feedback_evidence],
            'safety_rule_applied': bool(safety_evidence),
            'evidence_strength': strength,
            'retrieval_mode': 'hybrid_rag',
            'raw_evidence_provided': True,
        }

        return EvidencePack(
            all_evidence=items,
            selected_evidence=selected,
            discarded_evidence=discarded,
            rule_evidence=rule_evidence,
            historical_evidence=historical_evidence,
            safety_evidence=safety_evidence,
            evidence_summary=summary,
            evidence_strength=strength,
            evidence_trace=trace,
        )

    @staticmethod
    def _estimate_strength(selected: List[EvidenceItem]) -> str:
        if not selected:
            return 'low'
        has_rule = any(x.evidence_type == 'rule' for x in selected)
        has_history = any(x.evidence_type == 'historical_case' for x in selected)
        has_feedback = any(x.evidence_type == 'user_feedback' for x in selected)
        has_safety = any(x.priority >= 100 for x in selected)
        if has_rule and has_history and has_feedback and has_safety:
            return 'high'
        if has_rule and has_history and has_feedback:
            return 'medium'
        if (has_rule and has_history) or (has_rule and has_feedback):
            return 'medium'
        return 'low'


class EvidenceSummarizer:
    def summarize(self, selected: List[EvidenceItem]) -> str:
        if not selected:
            return '利用可能な根拠は限定的である。'

        rule_titles = []
        history_savings = []
        feedback_tags = []
        for item in selected:
            if item.evidence_type == 'rule':
                title = item.metadata.get('title') or item.support_target
                rule_titles.append(str(title))
            elif item.evidence_type == 'historical_case':
                history_savings.append(float(item.metadata.get('expected_saving_percent', 0.0) or 0.0))
            elif item.evidence_type == 'user_feedback':
                tag = item.metadata.get('preference_tag', '')
                if tag:
                    feedback_tags.append(str(tag))

        parts = []
        if rule_titles:
            parts.append(f"参照規則: {', '.join(rule_titles[:2])}")
        if history_savings:
            avg_hist = sum(history_savings) / len(history_savings)
            parts.append(f"参照履歴の平均節電率: 約{avg_hist:.1f}%")
        if feedback_tags:
            parts.append(f"参照ユーザー嗜好: {', '.join(feedback_tags[:2])}")
        parts.append('注: これはLLM入力用の整理表示であり、最終提案文の結論そのものではない')
        return '。'.join(parts) + '。'


class EvidenceOrchestrator:
    def __init__(self):
        self.collector = EvidenceCollector()
        self.selector = EvidenceSelector()

    def build_pack(self, proposal: ProposalSchema) -> EvidencePack:
        items = self.collector.collect(proposal)
        return self.selector.select(proposal, items)
