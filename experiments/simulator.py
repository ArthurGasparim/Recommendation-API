"""Simulador exploratório de ataques e resposta orientada por observabilidade.

Os valores deste módulo são cenários sintéticos determinísticos. Eles permitem
validar hipóteses, interface e protocolo antes de substituir os perfis pelos
resultados medidos no pipeline experimental.
"""

from __future__ import annotations

import math
from statistics import mean
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


AttackType = Literal[
    "push_attack",
    "nuke_attack",
    "data_corruption",
    "distribution_drift",
    "latency_degradation",
    "dependency_outage",
]


MODEL_CATALOG: dict[str, dict] = {
    "popularity": {
        "label": "Popularidade",
        "short_label": "Popularidade",
        "description": "Baseline não personalizado por volume e nota média.",
        "color": "#64748b",
        "baseline": {
            "ndcg_at_10": 0.43,
            "precision_at_10": 0.31,
            "recall_at_10": 0.24,
            "catalog_coverage": 0.19,
            "latency_p95_ms": 9.0,
            "availability_percent": 99.95,
            "data_quality_percent": 99.5,
        },
        "susceptibility": {
            "push_attack": 1.30,
            "nuke_attack": 1.15,
            "data_corruption": 0.75,
            "distribution_drift": 1.00,
            "latency_degradation": 0.65,
            "dependency_outage": 1.00,
        },
    },
    "content_tfidf": {
        "label": "Conteúdo TF-IDF",
        "short_label": "Conteúdo",
        "description": "Perfil por atributos, tags e similaridade de cosseno.",
        "color": "#0ea5e9",
        "baseline": {
            "ndcg_at_10": 0.64,
            "precision_at_10": 0.46,
            "recall_at_10": 0.38,
            "catalog_coverage": 0.63,
            "latency_p95_ms": 18.0,
            "availability_percent": 99.93,
            "data_quality_percent": 99.5,
        },
        "susceptibility": {
            "push_attack": 0.48,
            "nuke_attack": 0.52,
            "data_corruption": 1.20,
            "distribution_drift": 1.10,
            "latency_degradation": 0.82,
            "dependency_outage": 1.00,
        },
    },
    "item_item": {
        "label": "Colaborativo item-item",
        "short_label": "Item-item",
        "description": "Vizinhança de itens sobre matriz esparsa usuário-item.",
        "color": "#8b5cf6",
        "baseline": {
            "ndcg_at_10": 0.70,
            "precision_at_10": 0.51,
            "recall_at_10": 0.44,
            "catalog_coverage": 0.69,
            "latency_p95_ms": 27.0,
            "availability_percent": 99.92,
            "data_quality_percent": 99.5,
        },
        "susceptibility": {
            "push_attack": 0.98,
            "nuke_attack": 0.95,
            "data_corruption": 1.00,
            "distribution_drift": 0.92,
            "latency_degradation": 0.90,
            "dependency_outage": 1.00,
        },
    },
    "als": {
        "label": "ALS",
        "short_label": "ALS",
        "description": "Fatoração matricial com fatores latentes.",
        "color": "#f59e0b",
        "baseline": {
            "ndcg_at_10": 0.74,
            "precision_at_10": 0.55,
            "recall_at_10": 0.48,
            "catalog_coverage": 0.76,
            "latency_p95_ms": 34.0,
            "availability_percent": 99.91,
            "data_quality_percent": 99.5,
        },
        "susceptibility": {
            "push_attack": 1.16,
            "nuke_attack": 1.10,
            "data_corruption": 1.05,
            "distribution_drift": 0.86,
            "latency_degradation": 0.96,
            "dependency_outage": 1.00,
        },
    },
    "hybrid": {
        "label": "Híbrido",
        "short_label": "Híbrido",
        "description": "Combinação normalizada de conteúdo e colaborativo.",
        "color": "#10b981",
        "baseline": {
            "ndcg_at_10": 0.79,
            "precision_at_10": 0.60,
            "recall_at_10": 0.53,
            "catalog_coverage": 0.84,
            "latency_p95_ms": 44.0,
            "availability_percent": 99.90,
            "data_quality_percent": 99.5,
        },
        "susceptibility": {
            "push_attack": 0.72,
            "nuke_attack": 0.70,
            "data_corruption": 0.86,
            "distribution_drift": 0.72,
            "latency_degradation": 1.00,
            "dependency_outage": 1.00,
        },
    },
}


ATTACK_CATALOG: dict[str, dict] = {
    "push_attack": {
        "label": "Push attack",
        "short_label": "Push",
        "description": "Perfis artificiais promovem um item-alvo.",
        "color": "#f97316",
        "detection_delay": 4,
        "mitigation_minutes": 4,
        "remaining_impact": 0.22,
        "effects": {
            "ranking_loss": 0.32,
            "coverage_loss": 0.35,
            "latency_multiplier": 0.06,
            "availability_loss": 0.25,
            "data_quality_loss": 5.0,
        },
    },
    "nuke_attack": {
        "label": "Nuke attack",
        "short_label": "Nuke",
        "description": "Perfis artificiais prejudicam um item-alvo.",
        "color": "#ef4444",
        "detection_delay": 4,
        "mitigation_minutes": 4,
        "remaining_impact": 0.24,
        "effects": {
            "ranking_loss": 0.29,
            "coverage_loss": 0.24,
            "latency_multiplier": 0.05,
            "availability_loss": 0.20,
            "data_quality_loss": 5.0,
        },
    },
    "data_corruption": {
        "label": "Corrupção de dados",
        "short_label": "Dados inválidos",
        "description": "Duplicatas, campos ausentes e valores fora do domínio.",
        "color": "#dc2626",
        "detection_delay": 1,
        "mitigation_minutes": 3,
        "remaining_impact": 0.10,
        "effects": {
            "ranking_loss": 0.42,
            "coverage_loss": 0.31,
            "latency_multiplier": 0.15,
            "availability_loss": 1.2,
            "data_quality_loss": 31.0,
        },
    },
    "distribution_drift": {
        "label": "Drift de distribuição",
        "short_label": "Drift",
        "description": "Preferências e popularidade mudam em relação ao treino.",
        "color": "#d946ef",
        "detection_delay": 5,
        "mitigation_minutes": 6,
        "remaining_impact": 0.32,
        "effects": {
            "ranking_loss": 0.38,
            "coverage_loss": 0.22,
            "latency_multiplier": 0.03,
            "availability_loss": 0.10,
            "data_quality_loss": 11.0,
        },
    },
    "latency_degradation": {
        "label": "Degradação de latência",
        "short_label": "Latência",
        "description": "Consultas e inferências tornam-se progressivamente lentas.",
        "color": "#eab308",
        "detection_delay": 1,
        "mitigation_minutes": 2,
        "remaining_impact": 0.15,
        "effects": {
            "ranking_loss": 0.04,
            "coverage_loss": 0.02,
            "latency_multiplier": 3.2,
            "availability_loss": 4.5,
            "data_quality_loss": 0.0,
        },
    },
    "dependency_outage": {
        "label": "Indisponibilidade",
        "short_label": "Indisponibilidade",
        "description": "Banco ou dependência fica indisponível temporariamente.",
        "color": "#7c3aed",
        "detection_delay": 1,
        "mitigation_minutes": 2,
        "remaining_impact": 0.08,
        "effects": {
            "ranking_loss": 0.10,
            "coverage_loss": 0.12,
            "latency_multiplier": 5.0,
            "availability_loss": 36.0,
            "data_quality_loss": 0.0,
        },
    },
}


METRIC_CATALOG: dict[str, dict] = {
    "ndcg_at_10": {
        "label": "NDCG@10",
        "short_label": "NDCG",
        "description": "Qualidade e posição dos itens relevantes.",
        "unit": "ratio",
        "direction": "higher",
        "domain": [0, 1],
    },
    "precision_at_10": {
        "label": "Precision@10",
        "short_label": "Precision",
        "description": "Parcela da lista que é relevante.",
        "unit": "ratio",
        "direction": "higher",
        "domain": [0, 1],
    },
    "recall_at_10": {
        "label": "Recall@10",
        "short_label": "Recall",
        "description": "Parcela dos relevantes que foi recuperada.",
        "unit": "ratio",
        "direction": "higher",
        "domain": [0, 1],
    },
    "catalog_coverage": {
        "label": "Cobertura do catálogo",
        "short_label": "Cobertura",
        "description": "Parcela do catálogo presente nas recomendações.",
        "unit": "ratio",
        "direction": "higher",
        "domain": [0, 1],
    },
    "latency_p95_ms": {
        "label": "Latência p95",
        "short_label": "Latência",
        "description": "Tempo abaixo do qual 95% das respostas terminam.",
        "unit": "milliseconds",
        "direction": "lower",
        "domain": [0, None],
    },
    "availability_percent": {
        "label": "Disponibilidade",
        "short_label": "Disponibilidade",
        "description": "Percentual de requisições atendidas corretamente.",
        "unit": "percent",
        "direction": "higher",
        "domain": [0, 100],
    },
    "data_quality_percent": {
        "label": "Qualidade dos dados",
        "short_label": "Dados válidos",
        "description": "Percentual de registros válidos e consistentes.",
        "unit": "percent",
        "direction": "higher",
        "domain": [0, 100],
    },
}


class AttackSpec(BaseModel):
    attack_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,40}$")
    attack_type: AttackType
    start_minute: int = Field(ge=1, le=179)
    duration_minutes: int = Field(ge=1, le=120)
    intensity: float = Field(ge=0.05, le=1.0)


class SimulationRequest(BaseModel):
    duration_minutes: int = Field(default=60, ge=20, le=180)
    step_minutes: int = Field(default=1, ge=1, le=5)
    seed: int = Field(default=42, ge=0, le=1_000_000)
    models: list[str] = Field(
        default_factory=lambda: list(MODEL_CATALOG), min_length=1, max_length=5
    )
    attacks: list[AttackSpec] = Field(default_factory=list, max_length=8)
    compare_defense: bool = True

    @field_validator("models")
    @classmethod
    def validate_models(cls, value: list[str]) -> list[str]:
        unknown = sorted(set(value).difference(MODEL_CATALOG))
        if unknown:
            raise ValueError("Modelos desconhecidos: " + ", ".join(unknown))
        if len(value) != len(set(value)):
            raise ValueError("A lista de modelos não pode conter duplicatas")
        return value

    @model_validator(mode="after")
    def validate_timeline(self) -> "SimulationRequest":
        attack_ids = [attack.attack_id for attack in self.attacks]
        if len(attack_ids) != len(set(attack_ids)):
            raise ValueError("Cada ataque precisa de um attack_id único")
        for attack in self.attacks:
            if attack.start_minute + attack.duration_minutes > self.duration_minutes:
                raise ValueError(
                    f"O ataque {attack.attack_id} ultrapassa a duração da simulação"
                )
        return self


def simulation_catalog() -> dict:
    return {
        "kind": "exploratory_simulation",
        "disclaimer": (
            "Valores sintéticos para desenho experimental. Não representam "
            "resultados medidos nem comprovam superioridade de um modelo."
        ),
        "models": [
            {"id": model_id, **model}
            for model_id, model in MODEL_CATALOG.items()
        ],
        "attacks": [
            {"id": attack_id, **attack}
            for attack_id, attack in ATTACK_CATALOG.items()
        ],
        "metrics": [
            {"id": metric_id, **metric}
            for metric_id, metric in METRIC_CATALOG.items()
        ],
        "default_request": {
            "duration_minutes": 60,
            "step_minutes": 1,
            "seed": 42,
            "models": list(MODEL_CATALOG),
            "compare_defense": True,
            "attacks": [
                {
                    "attack_id": "dados-1",
                    "attack_type": "data_corruption",
                    "start_minute": 12,
                    "duration_minutes": 14,
                    "intensity": 0.55,
                },
                {
                    "attack_id": "push-1",
                    "attack_type": "push_attack",
                    "start_minute": 35,
                    "duration_minutes": 15,
                    "intensity": 0.65,
                },
            ],
        },
    }


def _attack_envelope(time: int, attack: AttackSpec) -> float:
    end = attack.start_minute + attack.duration_minutes
    if time < attack.start_minute:
        return 0.0
    if time <= end:
        return min(1.0, (time - attack.start_minute + 1) / 2.0)
    recovery_window = 4
    if time <= end + recovery_window:
        return max(0.0, 1.0 - (time - end) / recovery_window)
    return 0.0


def _defense_factor(time: int, attack: AttackSpec) -> float:
    definition = ATTACK_CATALOG[attack.attack_type]
    detection_time = attack.start_minute + definition["detection_delay"]
    if time < detection_time:
        return 1.0
    progress = (time - detection_time + 1) / definition["mitigation_minutes"]
    remaining = definition["remaining_impact"]
    return max(remaining, 1.0 - progress * (1.0 - remaining))


def _noise(time: int, seed: int, model_index: int) -> float:
    phase = time * 0.43 + seed * 0.017 + model_index * 1.91
    return math.sin(phase) * 0.004 + math.cos(phase * 0.61) * 0.002


def _round_point(point: dict[str, float | int]) -> dict[str, float | int]:
    rounded: dict[str, float | int] = {"time": int(point["time"])}
    for key, value in point.items():
        if key == "time":
            continue
        digits = 2 if key.endswith("_ms") or key.endswith("_percent") else 4
        rounded[key] = round(float(value), digits)
    return rounded


def _point_at_time(
    time: int,
    model_id: str,
    model_index: int,
    attacks: list[AttackSpec],
    defended: bool,
    seed: int,
) -> dict[str, float | int]:
    model = MODEL_CATALOG[model_id]
    baseline = model["baseline"]
    totals = {
        "ranking_loss": 0.0,
        "coverage_loss": 0.0,
        "latency_multiplier": 0.0,
        "availability_loss": 0.0,
        "data_quality_loss": 0.0,
    }

    for attack in attacks:
        envelope = _attack_envelope(time, attack)
        if envelope == 0:
            continue
        defense = _defense_factor(time, attack) if defended else 1.0
        susceptibility = model["susceptibility"][attack.attack_type]
        strength = attack.intensity * envelope * defense * susceptibility
        effects = ATTACK_CATALOG[attack.attack_type]["effects"]
        for effect_name in totals:
            totals[effect_name] += strength * effects[effect_name]

    quality_noise = _noise(time, seed, model_index)
    ranking_loss = min(0.88, totals["ranking_loss"])
    coverage_loss = min(0.90, totals["coverage_loss"])
    instrumentation_overhead = 0.04 if defended else 0.0

    point = {
        "time": time,
        "ndcg_at_10": max(
            0.0, min(1.0, baseline["ndcg_at_10"] * (1 - ranking_loss) + quality_noise)
        ),
        "precision_at_10": max(
            0.0,
            min(
                1.0,
                baseline["precision_at_10"] * (1 - min(0.90, ranking_loss * 1.06))
                + quality_noise * 0.8,
            ),
        ),
        "recall_at_10": max(
            0.0,
            min(
                1.0,
                baseline["recall_at_10"] * (1 - min(0.90, ranking_loss * 0.92))
                + quality_noise * 0.7,
            ),
        ),
        "catalog_coverage": max(
            0.0,
            min(
                1.0,
                baseline["catalog_coverage"] * (1 - coverage_loss)
                + quality_noise * 0.5,
            ),
        ),
        "latency_p95_ms": max(
            1.0,
            baseline["latency_p95_ms"]
            * (1 + totals["latency_multiplier"])
            * (1 + instrumentation_overhead),
        ),
        "availability_percent": max(
            0.0,
            min(
                100.0,
                baseline["availability_percent"] - totals["availability_loss"],
            ),
        ),
        "data_quality_percent": max(
            0.0,
            min(
                100.0,
                baseline["data_quality_percent"] - totals["data_quality_loss"],
            ),
        ),
    }
    return _round_point(point)


def _summarize(
    points: list[dict[str, float | int]],
    model_id: str,
    step_minutes: int,
    defended: bool,
    attacks: list[AttackSpec],
) -> dict:
    baseline_ndcg = MODEL_CATALOG[model_id]["baseline"]["ndcg_at_10"]
    quality_slo = baseline_ndcg * 0.90
    losses = [max(0.0, baseline_ndcg - float(point["ndcg_at_10"])) for point in points]
    return {
        "average_ndcg_at_10": round(mean(float(p["ndcg_at_10"]) for p in points), 4),
        "minimum_ndcg_at_10": round(min(float(p["ndcg_at_10"]) for p in points), 4),
        "average_precision_at_10": round(
            mean(float(p["precision_at_10"]) for p in points), 4
        ),
        "average_recall_at_10": round(
            mean(float(p["recall_at_10"]) for p in points), 4
        ),
        "average_catalog_coverage": round(
            mean(float(p["catalog_coverage"]) for p in points), 4
        ),
        "average_latency_p95_ms": round(
            mean(float(p["latency_p95_ms"]) for p in points), 2
        ),
        "minimum_availability_percent": round(
            min(float(p["availability_percent"]) for p in points), 2
        ),
        "accumulated_quality_loss": round(sum(losses) * step_minutes, 4),
        "minutes_below_quality_slo": sum(
            step_minutes
            for point in points
            if float(point["ndcg_at_10"]) < quality_slo
        ),
        "quality_slo": round(quality_slo, 4),
        "detections": len(attacks) if defended else 0,
        "mean_detection_minutes": (
            round(
                mean(
                    ATTACK_CATALOG[attack.attack_type]["detection_delay"]
                    for attack in attacks
                ),
                2,
            )
            if defended and attacks
            else None
        ),
        "instrumentation_latency_overhead_percent": 4.0 if defended else 0.0,
    }


def run_simulation(request: SimulationRequest) -> dict:
    times = list(range(0, request.duration_minutes + 1, request.step_minutes))
    if times[-1] != request.duration_minutes:
        times.append(request.duration_minutes)

    series: list[dict] = []
    defense_modes = [False, True] if request.compare_defense else [False]
    for model_index, model_id in enumerate(request.models):
        for defended in defense_modes:
            points = [
                _point_at_time(
                    time=time,
                    model_id=model_id,
                    model_index=model_index,
                    attacks=request.attacks,
                    defended=defended,
                    seed=request.seed,
                )
                for time in times
            ]
            series.append(
                {
                    "model": model_id,
                    "model_label": MODEL_CATALOG[model_id]["label"],
                    "color": MODEL_CATALOG[model_id]["color"],
                    "defended": defended,
                    "mode_label": (
                        "Com resposta observável" if defended else "Sem defesa"
                    ),
                    "points": points,
                    "summary": _summarize(
                        points,
                        model_id=model_id,
                        step_minutes=request.step_minutes,
                        defended=defended,
                        attacks=request.attacks,
                    ),
                }
            )

    events: list[dict] = []
    for attack in request.attacks:
        definition = ATTACK_CATALOG[attack.attack_type]
        events.append(
            {
                "time": attack.start_minute,
                "kind": "attack_start",
                "attack_id": attack.attack_id,
                "label": f"Início: {definition['label']}",
                "color": definition["color"],
            }
        )
        if request.compare_defense:
            events.append(
                {
                    "time": attack.start_minute + definition["detection_delay"],
                    "kind": "detection",
                    "attack_id": attack.attack_id,
                    "label": f"Detectado: {definition['label']}",
                    "color": "#10b981",
                }
            )
        events.append(
            {
                "time": attack.start_minute + attack.duration_minutes,
                "kind": "attack_end",
                "attack_id": attack.attack_id,
                "label": f"Fim: {definition['label']}",
                "color": definition["color"],
            }
        )
    events.sort(key=lambda event: (event["time"], event["kind"]))

    by_model: dict[str, dict[bool, dict]] = {}
    for item in series:
        by_model.setdefault(item["model"], {})[item["defended"]] = item["summary"]
    comparison: list[dict] = []
    for model_id in request.models:
        without = by_model[model_id][False]
        with_defense = by_model[model_id].get(True)
        loss_reduction = None
        if with_defense is not None and without["accumulated_quality_loss"] > 0:
            loss_reduction = round(
                100
                * (
                    without["accumulated_quality_loss"]
                    - with_defense["accumulated_quality_loss"]
                )
                / without["accumulated_quality_loss"],
                2,
            )
        comparison.append(
            {
                "model": model_id,
                "model_label": MODEL_CATALOG[model_id]["label"],
                "color": MODEL_CATALOG[model_id]["color"],
                "without_defense": without,
                "with_defense": with_defense,
                "quality_loss_reduction_percent": loss_reduction,
            }
        )

    return {
        "kind": "exploratory_simulation",
        "disclaimer": simulation_catalog()["disclaimer"],
        "duration_minutes": request.duration_minutes,
        "step_minutes": request.step_minutes,
        "seed": request.seed,
        "attacks": [
            {
                **attack.model_dump(),
                "label": ATTACK_CATALOG[attack.attack_type]["label"],
                "color": ATTACK_CATALOG[attack.attack_type]["color"],
                "detection_minute": (
                    attack.start_minute
                    + ATTACK_CATALOG[attack.attack_type]["detection_delay"]
                    if request.compare_defense
                    else None
                ),
            }
            for attack in request.attacks
        ],
        "events": events,
        "series": series,
        "comparison": comparison,
        "metric_catalog": METRIC_CATALOG,
    }

