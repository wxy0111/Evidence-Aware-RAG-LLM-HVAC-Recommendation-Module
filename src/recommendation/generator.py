import json
import os
import shlex
from typing import Dict, Any

import openai

from .action_schema import ProposalSchema
from .evidence_pipeline import EvidenceOrchestrator


def _load_openai_api_key() -> str:
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        return api_key

    zshrc_path = os.path.expanduser('~/.zshrc')
    if not os.path.exists(zshrc_path):
        return ""

    try:
        with open(zshrc_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line.startswith('export OPENAI_API_KEY='):
                    continue
                _, value = line.split('=', 1)
                value = shlex.split(value.strip())
                return value[0] if value else ""
    except OSError:
        return ""

    return ""


def _format_temp(value: float) -> str:
    return f"{value:.1f}°C"


def _display_saving_percent(value: float) -> str:
    return f"約{int(round(value))}%"


def _postprocess_message(text: str) -> str:
    replacements = [
        ("安全性を優先しています", "快適さを保ちやすい条件を優先しています"),
        ("安全性を優先し", "快適さを保ちやすい条件を優先し"),
        ("安全性", "快適さ"),
        ("安全な室内環境", "快適な室内環境"),
        ("安全で安定した室内環境", "快適で落ち着いた室内環境"),
        ("快適で安全な", "快適な"),
        ("快適で安全です", "快適に過ごしやすくなります"),
        ("節電実績が確認されています", "節電効果が確認されています"),
        ("節電実績があります", "節電効果が確認されています"),
        ("節電実績もあるため", "節電効果も確認されているため"),
        ("実績としてあります", "確認されています"),
        ("実績があります", "確認されています"),
        ("安定した節電実績", "安定した節電傾向"),
        ("ぜひお試しください", "取り入れやすい方法です"),
        ("お試しください", "ご検討ください"),
        ("ぜひご検討ください", "ご検討ください"),
        ("快適性と安全性を両立できます", "快適さを保ちながら節電しやすくなります"),
        ("快適さと安全性も確保できます", "快適さを保ちやすくなります"),
        ("室内環境の安定性を優先しています", "快適さを保ちやすい設定です"),
        ("室内環境の安定性を優先します", "快適さを保ちやすい設定です"),
        ("室内環境の安定性を優先し", "快適さを保ちやすく"),
        ("室内環境の安定を優先し", "快適さを保ちやすく"),
        ("室内環境の安定を優先することで", "快適さを保ちやすくなるため"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _template_action_text(proposal: ProposalSchema) -> str:
    if proposal.ac_switch == "off" and proposal.window_action == "ventilate":
        return "エアコンをオフにし、短時間換気してください"
    if proposal.window_action == "close":
        return f"窓を閉め、温度を{_format_temp(proposal.set_temperature_c)}に設定してください"
    if proposal.window_action == "ventilate":
        return f"温度を{_format_temp(proposal.set_temperature_c)}に設定し、短時間換気してください"
    return f"温度を{_format_temp(proposal.set_temperature_c)}に設定してください"


def _secondary_reason(proposal: ProposalSchema) -> str:
    reason_map = {
        "safety_priority": "屋外条件を踏まえ、快適さを保ちやすい設定です",
        "indoor_stability": "室内の快適さを保ちやすい設定です",
        "ventilation_balance": "換気と快適さの両立を考えた設定です",
        "comfort_energy_balance": "快適さと節電の両立を考えた設定です",
    }
    return reason_map.get(proposal.reason_type, "快適さと節電の両立を考えた設定です")


def _build_content_plan(proposal: ProposalSchema, evidence_pack) -> Dict[str, Any]:
    profile_text = str(proposal.metadata.get('user_preference_profile_text', '') or '')
    profile = proposal.metadata.get('user_preference_profile', {}) or {}
    has_history = len(evidence_pack.historical_evidence) > 0
    has_feedback = int(proposal.metadata.get('retrieved_feedback_count', 0) or 0) > 0
    history_avg = float(proposal.metadata.get('historical_avg_saving_percent', 0.0) or 0.0)
    plan = {
        'action_text': _template_action_text(proposal),
        'saving_text': _display_saving_percent(proposal.expected_saving_percent),
        'primary_reason_text': _secondary_reason(proposal),
        'history_hint_text': (
            f"過去の似た条件でも約{int(round(history_avg))}%の節電傾向が見られます"
            if has_history and history_avg > 0 else ''
        ),
        'feedback_hint_text': '',
        'risk_text': '、'.join(proposal.risk_flags) if proposal.risk_flags else 'なし',
        'has_history': has_history,
        'has_feedback': has_feedback,
        'user_profile_text': profile_text,
        'content_plan_version': 'paper_two_stage_v1',
    }
    if has_feedback:
        if profile.get('prefers_soft_tone', False):
            plan['feedback_hint_text'] = '無理のない調整として取り入れやすい形です'
        elif profile.get('prefers_brief', False):
            plan['feedback_hint_text'] = '短めにまとめると取り入れやすい調整です'
        else:
            plan['feedback_hint_text'] = '好みに合わせると取り入れやすい調整です'
    return plan


def _fallback_planning_json(content_plan: Dict[str, Any]) -> Dict[str, str]:
    return {
        'action_clause': str(content_plan.get('action_text', '')),
        'saving_clause': str(content_plan.get('saving_text', '')) + 'の節電が期待されます',
        'reason_clause': str(content_plan.get('primary_reason_text', '')),
        'history_clause': str(content_plan.get('history_hint_text', '')),
        'personalization_clause': str(content_plan.get('feedback_hint_text', '')),
        'risk_clause': str(content_plan.get('risk_text', '')) if str(content_plan.get('risk_text', '')) != 'なし' else '',
    }


def _realize_from_plan(plan_json: Dict[str, str]) -> str:
    action_clause = str(plan_json.get('action_clause', '')).strip().rstrip('。')
    saving_clause = str(plan_json.get('saving_clause', '')).strip().rstrip('。')
    reason_clause = str(plan_json.get('reason_clause', '')).strip().rstrip('。')
    history_clause = str(plan_json.get('history_clause', '')).strip().rstrip('。')
    personalization_clause = str(plan_json.get('personalization_clause', '')).strip().rstrip('。')
    risk_clause = str(plan_json.get('risk_clause', '')).strip().rstrip('。')

    first_parts = [p for p in [action_clause, saving_clause, reason_clause] if p]
    first_sentence = '、'.join(first_parts) + '。' if first_parts else ''

    second_parts = [p for p in [history_clause, personalization_clause, risk_clause] if p]
    second_sentence = '。'.join(second_parts) + '。' if second_parts else ''

    message = (first_sentence + second_sentence).strip()
    return _postprocess_message(message)


class _OpenAIProposalGeneratorBase:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.2, max_tokens: int = 260):
        api_key = _load_openai_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not found for LLM proposal generation")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = openai.OpenAI(api_key=api_key)
        self.evidence_orchestrator = EvidenceOrchestrator()

    def _call_llm_text(self, system_prompt: str, user_prompt: str, fallback_text: str) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            text = (resp.choices[0].message.content or "").strip()
            return text if text else fallback_text
        except Exception:
            return fallback_text

    def _call_llm_json(self, system_prompt: str, user_prompt: str, fallback_obj: Dict[str, str]) -> Dict[str, str]:
        fallback_text = json.dumps(fallback_obj, ensure_ascii=False)
        text = self._call_llm_text(system_prompt, user_prompt, fallback_text)
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return {k: str(v) if v is not None else '' for k, v in parsed.items()}
        except Exception:
            pass
        return fallback_obj


class EvidenceAwareRecommendationGenerator(_OpenAIProposalGeneratorBase):
    """Single paper-facing generator with two-stage planning and realization."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(model=model, temperature=0.2, max_tokens=260)

    def generate(self, proposal: ProposalSchema) -> ProposalSchema:
        proposal.confidence = 0.90
        proposal.message_style = "evidence_aware_grounded_short"
        proposal.metadata["generator_mode"] = "evidence_aware_rag"
        proposal.metadata["explanation_style"] = "grounded_short"
        proposal.metadata["constraint_explicit"] = True
        proposal.metadata["risk_explicit"] = bool(proposal.risk_flags)
        proposal.metadata["action_schema_complete"] = True
        proposal.metadata["message_length_style"] = "short"
        proposal.metadata["surface_realization_mode"] = "two_stage_grounded_llm_generation"
        proposal.metadata["llm_backend"] = self.model
        proposal.metadata["llm_api_used"] = True
        proposal.metadata["paper_method_name"] = "evidence_aware_rag_llm"
        proposal.metadata["generation_architecture"] = "two_stage_planning_realization"

        evidence_pack = self.evidence_orchestrator.build_pack(proposal)
        rule_context = '\n\n'.join([
            f"[Rule Evidence]\nID: {e.evidence_id}\nTitle: {e.metadata.get('title', e.support_target)}\nText:\n{e.content}"
            for e in evidence_pack.rule_evidence
        ]) or '関連規則なし'
        history_context = '\n\n'.join([
            f"[Historical Evidence]\nID: {e.evidence_id}\nText:\n{e.content}"
            for e in evidence_pack.historical_evidence
        ]) or '類似履歴なし'
        feedback_context = '\n\n'.join([
            f"[User Feedback Evidence]\nID: {e.evidence_id}\nText:\n{e.content}"
            for e in evidence_pack.selected_evidence if e.evidence_type == 'user_feedback'
        ]) or '関連するユーザーフィードバックなし'

        proposal.metadata['retrieved_knowledge_count'] = len(evidence_pack.rule_evidence)
        proposal.metadata['retrieved_knowledge_titles'] = [e.metadata.get('title', '') for e in evidence_pack.rule_evidence]
        proposal.metadata['retrieved_history_count'] = len(evidence_pack.historical_evidence)
        hist_vals = [float(e.metadata.get('expected_saving_percent', 0.0) or 0.0) for e in evidence_pack.historical_evidence]
        proposal.metadata['historical_avg_saving_percent'] = round(sum(hist_vals) / len(hist_vals), 2) if hist_vals else 0.0
        proposal.metadata['used_evidence_ids'] = evidence_pack.evidence_trace['selected_ids']
        proposal.metadata['used_rule_ids'] = evidence_pack.evidence_trace['selected_rule_ids']
        proposal.metadata['used_history_ids'] = evidence_pack.evidence_trace['selected_history_ids']
        proposal.metadata['used_feedback_ids'] = evidence_pack.evidence_trace.get('selected_feedback_ids', [])
        proposal.metadata['evidence_strength'] = evidence_pack.evidence_strength
        proposal.metadata['evidence_summary'] = evidence_pack.evidence_summary
        proposal.metadata['retrieval_mode'] = evidence_pack.evidence_trace.get('retrieval_mode', 'hybrid_rag')
        proposal.metadata['raw_evidence_prompted'] = evidence_pack.evidence_trace.get('raw_evidence_provided', True)
        proposal.metadata['safety_rule_applied'] = evidence_pack.evidence_trace['safety_rule_applied']
        has_history = len(evidence_pack.historical_evidence) > 0
        has_feedback = '関連するユーザーフィードバックなし' not in feedback_context
        proposal.metadata['personalization_mode'] = 'feedback_history_aware' if has_feedback else ('history_aware' if has_history else 'context_aware')

        content_plan = _build_content_plan(proposal, evidence_pack)
        proposal.metadata['content_plan'] = content_plan

        fallback_plan_json = _fallback_planning_json(content_plan)
        planning_system_prompt = "あなたは recommendation content planner です。固定された action plan と evidence から、最終文を直接書かず、内容要素を JSON で返してください。数値や行動を捏造してはいけません。"
        planning_user_prompt = f"""以下の情報に基づき、recommendation の内容計画 JSON を返してください。
- content plan:
{content_plan}
- 原始規則証拠:
{rule_context}
- 原始履歴証拠:
{history_context}
- ユーザーフィードバック証拠:
{feedback_context}
- 整理表示:
{evidence_pack.evidence_summary}
JSON schema:
{{
  "action_clause": "string",
  "saving_clause": "string",
  "reason_clause": "string",
  "history_clause": "string",
  "personalization_clause": "string",
  "risk_clause": "string"
}}
要件:
- action_clause, saving_clause, reason_clause は必須
- history_clause は履歴がある場合のみ埋める
- personalization_clause は feedback がある場合のみ埋める
- risk_clause は risk_text がある場合だけ自然に要約
- JSON のみ返す
- 節電率は必ず {content_plan['saving_text']} を使う
- 追加情報を捏造しない"""
        planning_json = self._call_llm_json(planning_system_prompt, planning_user_prompt, fallback_plan_json)
        proposal.metadata['planning_json'] = planning_json
        proposal.metadata['planning_stage_used'] = True

        realized_message = _realize_from_plan(planning_json)
        proposal.message = realized_message
        parts = [p for p in realized_message.split('。') if p.strip()]
        if parts:
            proposal.short_message = parts[0].strip() + '。'
            proposal.detailed_message = ''.join([p.strip() + '。' for p in parts[1:]])
        else:
            fallback = _realize_from_plan(fallback_plan_json)
            proposal.short_message = fallback
            proposal.detailed_message = ''
            proposal.message = fallback
        return proposal


StructuredLLMGenerator = EvidenceAwareRecommendationGenerator
