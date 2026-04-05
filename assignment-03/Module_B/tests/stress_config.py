from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class StressThresholds:
    minimum_success_rate: float
    maximum_p95_latency_ms: float
    maximum_invariant_violations: int


@dataclass(frozen=True)
class StressProfile:
    name: str
    users: int
    spawn_rate: int
    duration_seconds: int


STRESS_PROFILES: Dict[str, StressProfile] = {
    "baseline": StressProfile(
        name="baseline",
        users=24,
        spawn_rate=6,
        duration_seconds=180,
    ),
    "ramp": StressProfile(
        name="ramp",
        users=150,
        spawn_rate=15,
        duration_seconds=300,
    ),
    "spike": StressProfile(
        name="spike",
        users=300,
        spawn_rate=35,
        duration_seconds=120,
    ),
    "soak": StressProfile(
        name="soak",
        users=200,
        spawn_rate=20,
        duration_seconds=700,
    ),
    "breakpoint": StressProfile(
        name="breakpoint",
        users=500,
        spawn_rate=25,
        duration_seconds=180,
    ),
    "failure_under_load": StressProfile(
        name="failure_under_load",
        users=120,
        spawn_rate=12,
        duration_seconds=240,
    ),
}

DEFAULT_STRESS_THRESHOLDS = StressThresholds(
    minimum_success_rate=0.99,
    maximum_p95_latency_ms=1000.0,
    maximum_invariant_violations=0,
)


def get_stress_profile(name: str) -> StressProfile:
    try:
        return STRESS_PROFILES[name]
    except KeyError as exc:
        available = ", ".join(sorted(STRESS_PROFILES.keys()))
        raise ValueError(f"Unknown stress profile '{name}'. Available: {available}") from exc
