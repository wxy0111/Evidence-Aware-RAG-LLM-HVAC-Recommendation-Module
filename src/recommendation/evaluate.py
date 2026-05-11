from typing import List, Dict, Any
from collections import Counter
import ast


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {'true', '1', 'yes', 'y'}
    return False


def _normalize_metadata(metadata: Any) -> Dict[str, Any]:
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str) and metadata.strip():
        try:
            parsed = ast.literal_eval(metadata)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, SyntaxError):
            return {}
    return {}


def _contains_any(text: str, tokens: List[str]) -> bool:
    return any(token and token in text for token in tokens)


def _message_has_temperature(message: str) -> bool:
    return _contains_any(message, ['温度', '設定温度', '设定温度', '设定', '°C', '℃'])


def _message_has_ac_action(message: str) -> bool:
    return _contains_any(message, ['空调', 'エアコン', '冷房', '暖房', 'オフ', '停止'])


def _message_has_window_action(message: str) -> bool:
    return _contains_any(message, ['窗', '窓', '通风', '換気', '閉め', 'close'])


def _message_has_constraint_or_reason(message: str) -> bool:
    return _contains_any(message, [
        '快適', '節電', '負荷', '条件', '履歴', '類似', '傾向', '取り入れやすい',
        '无理', '無理', '理由', '安定', '換気', '屋外', '室外', '室内'
    ])


def evaluate_recommendations(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {
            "count": 0,
            "compliance_rate": 0.0,
            "avg_expected_saving_percent": 0.0,
            "median_expected_saving_percent": 0.0,
            "duplicate_rate": 0.0,
            "avg_message_length": 0.0,
            "action_diversity": 0.0,
            "risk_explicit_rate": 0.0,
            "constraint_explicit_rate": 0.0,
            "schema_completeness_rate": 0.0,
            "explanation_completeness_score": 0.0,
            "knowledge_used_rate": 0.0,
            "avg_retrieved_knowledge_count": 0.0,
            "knowledge_reflection_rate": 0.0,
            "historical_case_used_rate": 0.0,
            "avg_retrieved_history_count": 0.0,
            "historical_evidence_reflection_rate": 0.0,
            "feedback_used_rate": 0.0,
            "avg_retrieved_feedback_count": 0.0,
            "personalization_reflection_rate": 0.0,
            "high_evidence_strength_rate": 0.0,
            "medium_or_high_evidence_strength_rate": 0.0,
            "auto_repair_rate": 0.0,
            "safety_rule_application_rate": 0.0,
            "evidence_trace_completeness_rate": 0.0,
            "top_error": "",
        }

    valid_count = sum(1 for r in records if r.get("is_valid", False))
    savings = [float(r.get("expected_saving_percent", 0.0)) for r in records]
    avg_saving = sum(savings) / len(records)
    sorted_savings = sorted(savings)
    n = len(sorted_savings)
    if n % 2 == 1:
        median_saving = sorted_savings[n // 2]
    else:
        median_saving = (sorted_savings[n // 2 - 1] + sorted_savings[n // 2]) / 2.0

    duplicate_count = 0
    for i in range(1, len(records)):
        if records[i].get("message") == records[i - 1].get("message"):
            duplicate_count += 1

    lengths = [len(str(r.get("message", ""))) for r in records]
    avg_message_length = sum(lengths) / len(lengths) if lengths else 0.0

    action_keys = [
        f"{r.get('set_temperature_c')}|{r.get('ac_switch')}|{r.get('window_action')}"
        for r in records
    ]
    unique_actions = len(set(action_keys))

    risk_explicit_count = 0
    constraint_explicit_count = 0
    schema_complete_count = 0
    explanation_complete_count = 0
    knowledge_used_count = 0
    total_retrieved_knowledge_count = 0
    knowledge_reflection_count = 0
    historical_case_used_count = 0
    total_retrieved_history_count = 0
    historical_evidence_reflection_count = 0
    feedback_used_count = 0
    total_retrieved_feedback_count = 0
    personalization_reflection_count = 0
    high_evidence_strength_count = 0
    medium_or_high_evidence_strength_count = 0
    auto_repair_count = 0
    safety_rule_application_count = 0
    evidence_trace_complete_count = 0

    for r in records:
        metadata = _normalize_metadata(r.get('metadata', {}))
        message = str(r.get('message', ''))

        if metadata.get('risk_explicit'):
            risk_explicit_count += 1
        if metadata.get('constraint_explicit'):
            constraint_explicit_count += 1

        retrieved_knowledge_count = int(metadata.get('retrieved_knowledge_count', 0) or 0)
        total_retrieved_knowledge_count += retrieved_knowledge_count
        if retrieved_knowledge_count > 0:
            knowledge_used_count += 1

        retrieved_titles = metadata.get('retrieved_knowledge_titles', [])
        if isinstance(retrieved_titles, str):
            try:
                parsed_titles = ast.literal_eval(retrieved_titles)
                retrieved_titles = parsed_titles if isinstance(parsed_titles, list) else []
            except (ValueError, SyntaxError):
                retrieved_titles = []
        title_tokens = []
        for title in retrieved_titles:
            title = str(title)
            title_tokens.extend([tok for tok in title.replace('・', ' ').replace('と', ' ').split() if tok])
            title_tokens.extend([title])
        if any(token and token in message for token in title_tokens):
            knowledge_reflection_count += 1

        retrieved_history_count = int(metadata.get('retrieved_history_count', 0) or 0)
        total_retrieved_history_count += retrieved_history_count
        if retrieved_history_count > 0:
            historical_case_used_count += 1

        retrieved_feedback_count = int(metadata.get('retrieved_feedback_count', 0) or 0)
        total_retrieved_feedback_count += retrieved_feedback_count
        if retrieved_feedback_count > 0:
            feedback_used_count += 1

        if _contains_any(message, [
            '過去', '類似条件', '似た条件', '同様の条件', '過去のケース', '履歴',
            'これまで', '実績', '節電傾向', '過去の似た条件'
        ]):
            historical_evidence_reflection_count += 1

        if _contains_any(message, [
            '好み', '普段', '受け入れやすい', '無理のない', '取り入れやすい',
            '合わせると', '短めにまとめると', 'やわらかく', '段階的に',
            '少しずつ', '午後は', '朝は', '騒音', '開けすぎず'
        ]):
            personalization_reflection_count += 1

        strength = str(metadata.get('evidence_strength', '')).lower()
        if strength == 'high':
            high_evidence_strength_count += 1
        if strength in {'medium', 'high'}:
            medium_or_high_evidence_strength_count += 1

        if r.get('auto_repaired'):
            auto_repair_count += 1
        if metadata.get('safety_rule_applied'):
            safety_rule_application_count += 1
        if metadata.get('used_evidence_ids') and metadata.get('evidence_summary'):
            evidence_trace_complete_count += 1

        has_temp_field = r.get('set_temperature_c') is not None
        has_ac_field = r.get('ac_switch') in {'on', 'off'}
        has_window_field = r.get('window_action') in {'open', 'close', 'ventilate'}
        if has_temp_field and has_ac_field and has_window_field:
            schema_complete_count += 1

        has_temp_expr = _message_has_temperature(message)
        has_ac_expr = _message_has_ac_action(message)
        has_window_expr = _message_has_window_action(message)
        has_reason_expr = _message_has_constraint_or_reason(message)
        if has_temp_expr and has_ac_expr and has_window_expr and has_reason_expr:
            explanation_complete_count += 1

    errors = []
    for r in records:
        err = r.get("errors", "")
        if isinstance(err, str) and err:
            errors.extend([e for e in err.split('|') if e])
    top_error = Counter(errors).most_common(1)[0][0] if errors else ""

    return {
        "count": len(records),
        "compliance_rate": valid_count / len(records),
        "avg_expected_saving_percent": avg_saving,
        "median_expected_saving_percent": median_saving,
        "duplicate_rate": duplicate_count / max(1, len(records) - 1),
        "avg_message_length": avg_message_length,
        "action_diversity": unique_actions / max(1, len(records)),
        "risk_explicit_rate": risk_explicit_count / max(1, len(records)),
        "constraint_explicit_rate": constraint_explicit_count / max(1, len(records)),
        "schema_completeness_rate": schema_complete_count / max(1, len(records)),
        "explanation_completeness_score": explanation_complete_count / max(1, len(records)),
        "knowledge_used_rate": knowledge_used_count / max(1, len(records)),
        "avg_retrieved_knowledge_count": total_retrieved_knowledge_count / max(1, len(records)),
        "knowledge_reflection_rate": knowledge_reflection_count / max(1, len(records)),
        "historical_case_used_rate": historical_case_used_count / max(1, len(records)),
        "avg_retrieved_history_count": total_retrieved_history_count / max(1, len(records)),
        "historical_evidence_reflection_rate": historical_evidence_reflection_count / max(1, len(records)),
        "feedback_used_rate": feedback_used_count / max(1, len(records)),
        "avg_retrieved_feedback_count": total_retrieved_feedback_count / max(1, len(records)),
        "personalization_reflection_rate": personalization_reflection_count / max(1, len(records)),
        "high_evidence_strength_rate": high_evidence_strength_count / max(1, len(records)),
        "medium_or_high_evidence_strength_rate": medium_or_high_evidence_strength_count / max(1, len(records)),
        "auto_repair_rate": auto_repair_count / max(1, len(records)),
        "safety_rule_application_rate": safety_rule_application_count / max(1, len(records)),
        "evidence_trace_completeness_rate": evidence_trace_complete_count / max(1, len(records)),
        "top_error": top_error,
    }
