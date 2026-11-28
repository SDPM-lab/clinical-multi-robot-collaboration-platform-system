from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict

from config import (
    SERVICE_TIME_CONFIG,
    TASK_WASTE,
    TASK_CLOTHES,
    TASK_MEDICATION,
    TASK_SPECIMEN,
    TASK_WARD,
)


@dataclass(frozen=True)
class ServiceTimeSample:
    task_type: str
    total_s: float

    # optional breakdown
    detect_s: float = 0.0
    pick_s: float = 0.0
    drop_s: float = 0.0
    load_s: float = 0.0
    handoff_s: float = 0.0
    load_verify_s: float = 0.0
    receive_s: float = 0.0
    vital_sign_s: float = 0.0

    item_count: int = 0


class ServiceTimeModel:
    def sample(
        self,
        task_type: str,
        rng: random.Random,
    ) -> ServiceTimeSample:

        if task_type == TASK_WASTE:
            return self._sample_waste(rng)

        if task_type == TASK_CLOTHES:
            return self._sample_clothes(rng)

        if task_type == TASK_MEDICATION:
            return self._sample_medication(rng)

        if task_type == TASK_SPECIMEN:
            return self._sample_specimen(rng)

        if task_type == TASK_WARD:
            return self._sample_ward(rng)

        raise ValueError(
            f"Unsupported task type: {task_type}"
        )

    def _sample_waste(
        self,
        rng: random.Random,
    ) -> ServiceTimeSample:
        cfg = SERVICE_TIME_CONFIG[TASK_WASTE]

        detect_s = rng.uniform(
            *cfg["detect_s"]
        )

        item_count = self._sample_discrete_count(
            cfg["item_count_probabilities"],
            rng,
        )

        total_pick_s = 0.0
        total_drop_s = 0.0

        for _ in range(item_count):
            total_pick_s += rng.uniform(
                *cfg["pick_per_item_s"]
            )

            total_drop_s += rng.uniform(
                *cfg["drop_per_item_s"]
            )

        total_s = (
            detect_s
            + total_pick_s
            + total_drop_s
        )

        return ServiceTimeSample(
            task_type=TASK_WASTE,
            total_s=total_s,
            detect_s=detect_s,
            pick_s=total_pick_s,
            drop_s=total_drop_s,
            item_count=item_count,
        )

    def _sample_clothes(
        self,
        rng: random.Random,
    ) -> ServiceTimeSample:
        cfg = SERVICE_TIME_CONFIG[TASK_CLOTHES]

        detect_s = rng.uniform(
            *cfg["detect_s"]
        )

        item_count = self._sample_discrete_count(
            cfg["item_count_probabilities"],
            rng,
        )

        total_pick_s = 0.0
        total_drop_s = 0.0

        for _ in range(item_count):
            total_pick_s += rng.uniform(
                *cfg["pick_per_item_s"]
            )

            total_drop_s += rng.uniform(
                *cfg["drop_per_item_s"]
            )

        total_s = (
            detect_s
            + total_pick_s
            + total_drop_s
        )

        return ServiceTimeSample(
            task_type=TASK_CLOTHES,
            total_s=total_s,
            detect_s=detect_s,
            pick_s=total_pick_s,
            drop_s=total_drop_s,
            item_count=item_count,
        )

    def _sample_medication(
        self,
        rng: random.Random,
    ) -> ServiceTimeSample:
        cfg = SERVICE_TIME_CONFIG[TASK_MEDICATION]

        load_s = rng.uniform(
            *cfg["load_s"]
        )

        handoff_s = rng.uniform(
            *cfg["handoff_s"]
        )

        total_s = load_s + handoff_s

        return ServiceTimeSample(
            task_type=TASK_MEDICATION,
            total_s=total_s,
            load_s=load_s,
            handoff_s=handoff_s,
        )

    def _sample_specimen(
        self,
        rng: random.Random,
    ) -> ServiceTimeSample:
        cfg = SERVICE_TIME_CONFIG[TASK_SPECIMEN]

        load_verify_s = rng.uniform(
            *cfg["load_verify_s"]
        )

        receive_s = rng.uniform(
            *cfg["receive_s"]
        )

        total_s = (
            load_verify_s
            + receive_s
        )

        return ServiceTimeSample(
            task_type=TASK_SPECIMEN,
            total_s=total_s,
            load_verify_s=load_verify_s,
            receive_s=receive_s,
        )

    def _sample_ward(
        self,
        rng: random.Random,
    ) -> ServiceTimeSample:
        cfg = SERVICE_TIME_CONFIG[TASK_WARD]

        vital_sign_s = rng.uniform(
            *cfg["vital_sign_s"]
        )

        return ServiceTimeSample(
            task_type=TASK_WARD,
            total_s=vital_sign_s,
            vital_sign_s=vital_sign_s,
        )

    @staticmethod
    def _sample_discrete_count(
        probabilities: Dict[int, float],
        rng: random.Random,
    ) -> int:
        counts = list(probabilities.keys())
        weights = list(probabilities.values())

        total_probability = sum(weights)

        if abs(total_probability - 1.0) > 1e-9:
            raise ValueError(
                "Item count probabilities must sum to 1.0, "
                f"got {total_probability}"
            )

        return rng.choices(
            population=counts,
            weights=weights,
            k=1,
        )[0]


if __name__ == "__main__":
    rng = random.Random(42)
    model = ServiceTimeModel()

    task_types = [
        TASK_WASTE,
        TASK_CLOTHES,
        TASK_MEDICATION,
        TASK_SPECIMEN,
        TASK_WARD,
    ]

    for task_type in task_types:
        sample = model.sample(
            task_type,
            rng,
        )

        print(sample)