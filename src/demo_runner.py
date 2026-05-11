from datetime import datetime
from recommendation.policy import RecommendationPolicy
from recommendation.action_constructor import ActionConstructor
from recommendation.validator import ProposalValidator
from recommendation.generator import EvidenceAwareRecommendationGenerator
from recommendation.evaluate import evaluate_recommendations


def main():
    policy = RecommendationPolicy()
    constructor = ActionConstructor()
    validator = ProposalValidator()
    generator = EvidenceAwareRecommendationGenerator()

    samples = [
        {
            "timestamp": datetime(2024, 11, 19, 9, 0),
            "is_working_hour": True,
            "current_temp": 27.0,
            "optimal_temp": 25.0,
            "indoor_temp": 27.0,
            "outdoor_temp": 30.0,
            "saving_percent": 8.2,
        },
        {
            "timestamp": datetime(2024, 11, 19, 10, 0),
            "is_working_hour": True,
            "current_temp": 25.5,
            "optimal_temp": 25.0,
            "indoor_temp": 25.5,
            "outdoor_temp": 24.0,
            "saving_percent": 3.1,
        },
    ]

    records = []
    last_time = None
    for sample in samples:
        ok, reason = policy.should_trigger(
            timestamp=sample["timestamp"],
            is_working_hour=sample["is_working_hour"],
            current_temp=sample["current_temp"],
            optimal_temp=sample["optimal_temp"],
            saving_percent=sample["saving_percent"],
            last_proposal_time=last_time,
        )
        if not ok:
            continue

        proposal = constructor.build(
            timestamp=sample["timestamp"].isoformat(),
            current_temp=sample["current_temp"],
            optimal_temp=sample["optimal_temp"],
            indoor_temp=sample["indoor_temp"],
            outdoor_temp=sample["outdoor_temp"],
            saving_percent=sample["saving_percent"],
        )
        proposal = generator.generate(proposal)
        result = validator.validate(
            proposal,
            current_temp=sample["current_temp"],
            indoor_temp=sample["indoor_temp"],
            outdoor_temp=sample["outdoor_temp"],
            expected_saving_percent=sample["saving_percent"],
        )
        repair_result = validator.auto_repair(proposal)
        result = validator.validate(
            proposal,
            current_temp=sample["current_temp"],
            indoor_temp=sample["indoor_temp"],
            outdoor_temp=sample["outdoor_temp"],
            expected_saving_percent=sample["saving_percent"],
        )
        d = proposal.to_dict()
        d["is_valid"] = result.is_valid
        d["errors"] = result.errors
        d["warnings"] = result.warnings + repair_result.warnings
        d["trigger_reason"] = reason
        records.append(d)
        last_time = sample["timestamp"]

    summary = evaluate_recommendations(records)
    print(summary)
    for r in records:
        print(r["message"])


if __name__ == "__main__":
    main()
