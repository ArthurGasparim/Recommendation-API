import pytest
from pydantic import ValidationError

from experiments.simulator import (
    SimulationRequest,
    run_simulation,
    simulation_catalog,
)


def request_with_attack(**overrides):
    payload = {
        "duration_minutes": 40,
        "step_minutes": 1,
        "seed": 17,
        "models": ["hybrid"],
        "compare_defense": True,
        "attacks": [
            {
                "attack_id": "corrupcao-1",
                "attack_type": "data_corruption",
                "start_minute": 10,
                "duration_minutes": 12,
                "intensity": 0.7,
            }
        ],
    }
    payload.update(overrides)
    return SimulationRequest(**payload)


def series_for(result, defended):
    return next(item for item in result["series"] if item["defended"] is defended)


def point_at(series, minute):
    return next(point for point in series["points"] if point["time"] == minute)


def test_catalog_marks_values_as_exploratory_and_lists_all_dimensions():
    catalog = simulation_catalog()

    assert catalog["kind"] == "exploratory_simulation"
    assert "Não representam resultados medidos" in catalog["disclaimer"]
    assert len(catalog["models"]) == 5
    assert len(catalog["attacks"]) == 6
    assert {metric["id"] for metric in catalog["metrics"]} >= {
        "ndcg_at_10",
        "precision_at_10",
        "latency_p95_ms",
        "availability_percent",
    }


def test_request_rejects_unknown_models_duplicate_ids_and_out_of_range_attacks():
    with pytest.raises(ValidationError):
        request_with_attack(models=["unknown"])

    with pytest.raises(ValidationError):
        request_with_attack(
            attacks=[
                {
                    "attack_id": "same",
                    "attack_type": "push_attack",
                    "start_minute": 5,
                    "duration_minutes": 5,
                    "intensity": 0.5,
                },
                {
                    "attack_id": "same",
                    "attack_type": "nuke_attack",
                    "start_minute": 15,
                    "duration_minutes": 5,
                    "intensity": 0.5,
                },
            ]
        )

    with pytest.raises(ValidationError):
        request_with_attack(
            attacks=[
                {
                    "attack_id": "too-late",
                    "attack_type": "distribution_drift",
                    "start_minute": 35,
                    "duration_minutes": 10,
                    "intensity": 0.5,
                }
            ]
        )


def test_simulation_is_deterministic_and_defense_only_changes_quality_after_detection():
    request = request_with_attack()
    first = run_simulation(request)
    second = run_simulation(request)

    assert first == second
    without = series_for(first, False)
    defended = series_for(first, True)

    assert point_at(without, 9)["ndcg_at_10"] == point_at(defended, 9)["ndcg_at_10"]
    assert point_at(without, 10)["ndcg_at_10"] == point_at(defended, 10)["ndcg_at_10"]
    assert point_at(defended, 14)["ndcg_at_10"] > point_at(without, 14)["ndcg_at_10"]
    assert point_at(defended, 9)["latency_p95_ms"] > point_at(without, 9)["latency_p95_ms"]


def test_observable_response_reduces_accumulated_loss_and_records_events():
    result = run_simulation(request_with_attack())
    comparison = result["comparison"][0]
    without = comparison["without_defense"]
    defended = comparison["with_defense"]

    assert defended["accumulated_quality_loss"] < without["accumulated_quality_loss"]
    assert comparison["quality_loss_reduction_percent"] > 0
    assert defended["detections"] == 1
    assert [event["kind"] for event in result["events"]] == [
        "attack_start",
        "detection",
        "attack_end",
    ]


def test_simulation_without_attacks_preserves_quality_around_model_baseline():
    request = SimulationRequest(
        duration_minutes=20,
        models=["content_tfidf"],
        attacks=[],
        compare_defense=True,
    )
    result = run_simulation(request)
    without = series_for(result, False)
    defended = series_for(result, True)

    assert abs(without["summary"]["average_ndcg_at_10"] - 0.64) < 0.01
    assert without["summary"]["average_ndcg_at_10"] == defended["summary"][
        "average_ndcg_at_10"
    ]
    assert defended["summary"]["instrumentation_latency_overhead_percent"] == 4.0

