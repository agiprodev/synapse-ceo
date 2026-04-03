from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class HumanFeedbackStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    WRONG = "wrong"

@dataclass
class MachineMetrics:
    health_status: str  # "healthy" | "unhealthy"
    cpu_before: float
    cpu_after: float
    errors_before: int
    errors_after: int

@dataclass
class RewardResult:
    machine_score: float
    human_score: float
    final_reward_score: float
    cpu_drop_percent: float
    errors_count_delta: int
    health_status: str
    learning_tag: str  # "SUCCESS_STABLE", "PARTIAL_IMPROVEMENT", "FAILED_REGRESSION"

def calculate_reward(
    metrics: MachineMetrics,
    human_status: HumanFeedbackStatus = HumanFeedbackStatus.PENDING,
    regressed: bool = False
) -> RewardResult:
    # 1. Calculate Machine Score (Base 1.0)
    cpu_delta = metrics.cpu_before - metrics.cpu_after
    error_delta = metrics.errors_before - metrics.errors_after
    
    # Base logic: improvement vs regression
    machine_score = 0.5 # Neutral start
    
    if metrics.health_status == "healthy":
        machine_score += 0.2
    else:
        machine_score -= 0.5

    if cpu_delta > 0: machine_score += 0.1
    if error_delta > 0: machine_score += 0.2
    if regressed: machine_score -= 0.4

    # 2. Calculate Human Score
    human_score = 0.0
    if human_status == HumanFeedbackStatus.SUCCESS:
        human_score = 1.0
    elif human_status == HumanFeedbackStatus.WRONG:
        human_score = -1.0

    # 3. Final Reward Calculation
    final_score = (machine_score * 0.7) + (human_score * 0.3)
    
    # Tagging for Learning Memory
    tag = "SUCCESS_STABLE"
    if final_score < 0.3: tag = "FAILED_REGRESSION"
    elif final_score < 0.7: tag = "PARTIAL_IMPROVEMENT"

    return RewardResult(
        machine_score=round(machine_score, 2),
        human_score=human_score,
        final_reward_score=round(final_score, 2),
        cpu_drop_percent=round(cpu_delta, 2),
        errors_count_delta=error_delta,
        health_status=metrics.health_status,
        learning_tag=tag
    )
