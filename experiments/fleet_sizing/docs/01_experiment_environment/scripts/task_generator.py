from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from config import (
    SIMULATION_DAYS,
    SECONDS_PER_DAY,

    TASK_WASTE,
    TASK_CLOTHES,
    TASK_MEDICATION,
    TASK_SPECIMEN,
    TASK_WARD,
    TASK_PRIORITY_DISTRIBUTIONS,

    WASTE_SOURCES,
    WASTE_DESTINATION,

    CLOTHES_SOURCES,
    CLOTHES_DESTINATION,

    MEDICATION_SOURCE,
    MEDICATION_DESTINATIONS,

    SPECIMEN_CLINICAL_LOCATIONS,
    SPECIMEN_LAB,

    WARD_SOURCE,
    WARD_DESTINATIONS,

    WASTE_ARRIVAL_WINDOW,

    CLOTHES_DAILY_PROBABILITY_PER_SOURCE,
    CLOTHES_ARRIVAL_WINDOW,

    NORMAL_WORKLOAD_PER_DAY,

    MEDICATION_SCHEDULED_FRACTION,
    MEDICATION_SCHEDULED_BASE_HOURS,
    MEDICATION_SCHEDULED_JITTER_MINUTES,
    MEDICATION_ON_DEMAND_TIME_WEIGHTS,

    SPECIMEN_TIME_WEIGHTS,
    SPECIMEN_CLINICAL_TO_LAB_PROBABILITY,

    WARD_BASE_HOURS,
    WARD_JITTER_MINUTES,
)

from service_time import ServiceTimeModel


@dataclass(frozen=True)
class GeneratedTask:
    task_id: str
    task_type: str
    source: str
    destination: str
    arrival_time_s: float
    priority: int
    service_time_s: float


class NormalTaskGenerator:
    """
    Generate stochastic Normal Workload tasks.

    Important:
    NORMAL_WORKLOAD_PER_DAY represents expected daily workload,
    not an exact number of tasks every day.

    Expected daily workload:
        Waste      ~= 11/day
        Clothes    ~= 3/day
        Medication ~= 22/day
        Specimen   ~= 18/day
        Ward       = 4/day

        Total      ~= 58/day
    """

    def __init__(
        self,
        seed: int,
        workload_multiplier: float = 1.0,
    ):
        if workload_multiplier <= 0:
            raise ValueError(
                "workload_multiplier must be > 0"
            )

        self.seed = seed
        self.workload_multiplier = workload_multiplier

        self.arrival_rng = random.Random(seed)
        self.service_rng = random.Random(
            seed + 10_000_000
        )

        self.service_model = ServiceTimeModel()

        self._counter = 0

    # ============================================================
    # Public API
    # ============================================================

    def generate(self) -> List[GeneratedTask]:
        tasks: List[GeneratedTask] = []

        for day in range(SIMULATION_DAYS):
            tasks.extend(
                self._generate_waste(day)
            )

            tasks.extend(
                self._generate_clothes(day)
            )

            tasks.extend(
                self._generate_medication(day)
            )

            tasks.extend(
                self._generate_specimen(day)
            )

            tasks.extend(
                self._generate_ward(day)
            )

        # Simulation processes tasks chronologically.
        tasks.sort(
            key=lambda task: task.arrival_time_s
        )

        return tasks

    # ============================================================
    # Generic helpers
    # ============================================================

    def _new_task(
        self,
        task_type: str,
        source: str,
        destination: str,
        arrival_time_s: float,
        priority: int | None = None,
    ) -> GeneratedTask:

        if source == destination:
            raise ValueError(
                "Task source and destination cannot be identical: "
                f"{source}"
            )

        self._counter += 1

        if priority is None:
            priority = self._sample_priority(
                task_type
            )

        service_sample = (
            self.service_model.sample(
                task_type,
                self.service_rng,
            )
        )

        return GeneratedTask(
            task_id=f"T{self._counter:05d}",
            task_type=task_type,
            source=source,
            destination=destination,
            arrival_time_s=arrival_time_s,
            priority=priority,
            service_time_s=(
                service_sample.total_s
            ),
        )

    @staticmethod
    def _poisson(
        lam: float,
        rng: random.Random,
    ) -> int:
        """
        Sample Poisson(lam) using Knuth's algorithm.

        Suitable here because all lambda values are small.
        No NumPy dependency is required.
        """

        if lam < 0:
            raise ValueError(
                f"Poisson lambda must be >= 0, got {lam}"
            )

        if lam == 0:
            return 0

        threshold = math.exp(-lam)

        k = 0
        product = 1.0

        while product > threshold:
            k += 1
            product *= rng.random()

        return k - 1

    @staticmethod
    def _validate_weights(
        weights: Dict[Tuple[int, int], float],
    ) -> None:

        total = sum(weights.values())

        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                "Time-block weights must sum to 1.0, "
                f"got {total}"
            )

    def _day_offset(
        self,
        day: int,
    ) -> float:
        return day * SECONDS_PER_DAY

    def _random_time_in_window(
        self,
        day: int,
        start_hour: float,
        end_hour: float,
    ) -> float:

        start_s = start_hour * 3600.0
        end_s = end_hour * 3600.0

        return (
            self._day_offset(day)
            + self.arrival_rng.uniform(
                start_s,
                end_s,
            )
        )

    def _sample_priority(
        self,
        task_type: str,
    ) -> int:

        distribution = (
            TASK_PRIORITY_DISTRIBUTIONS[
                task_type
            ]
        )

        priorities = list(
            distribution.keys()
        )

        probabilities = list(
            distribution.values()
        )

        total = sum(probabilities)

        if abs(total - 1.0) > 1e-9:
            raise ValueError(
                f"Priority probabilities for "
                f"{task_type} must sum to 1.0, "
                f"got {total}"
            )

        return self.arrival_rng.choices(
            population=priorities,
            weights=probabilities,
            k=1,
        )[0]

    # ============================================================
    # Waste Transport
    # ============================================================

    def _generate_waste(
        self,
        day: int,
    ) -> List[GeneratedTask]:

        tasks: List[GeneratedTask] = []

        total_expected = NORMAL_WORKLOAD_PER_DAY[
            TASK_WASTE
        ]

        # 11 legal sources and expected total 11/day:
        #
        # lambda_per_source = 1 task/source/day.
        #
        # Each source can therefore have:
        # 0, 1, 2, ... waste tasks on a given day.
        #
        # Sum across sources still has expected value 11/day.
        lam_per_source = (
            total_expected
            * self.workload_multiplier
            / len(WASTE_SOURCES)
        )

        for source in WASTE_SOURCES:

            daily_count = self._poisson(
                lam_per_source,
                self.arrival_rng,
            )

            for _ in range(daily_count):

                arrival = self._random_time_in_window(
                    day,
                    WASTE_ARRIVAL_WINDOW[
                        "start_hour"
                    ],
                    WASTE_ARRIVAL_WINDOW[
                        "end_hour"
                    ],
                )

                tasks.append(
                    self._new_task(
                        task_type=TASK_WASTE,
                        source=source,
                        destination=WASTE_DESTINATION,
                        arrival_time_s=arrival,
                    )
                )

        return tasks

    # ============================================================
    # Clothes Collection
    # ============================================================

    def _generate_clothes(
        self,
        day: int,
    ) -> List[GeneratedTask]:

        tasks: List[GeneratedTask] = []

        base_probability = (
            CLOTHES_DAILY_PROBABILITY_PER_SOURCE
        )

        multiplier = (
            self.workload_multiplier
        )

        for source in CLOTHES_SOURCES:

            # Normal workload:
            # 保留原本 Bernoulli(0.5)
            if multiplier == 1.0:

                daily_count = (
                    1
                    if self.arrival_rng.random()
                    < base_probability
                    else 0
                )

            # Low workload:
            # Bernoulli probability proportional reduction
            elif multiplier < 1.0:

                probability = (
                    base_probability
                    * multiplier
                )

                daily_count = (
                    1
                    if self.arrival_rng.random()
                    < probability
                    else 0
                )

            # High workload:
            #
            # 先保留 Normal 的 Bernoulli demand，
            # 再增加額外 Poisson arrivals。
            else:

                base_count = (
                    1
                    if self.arrival_rng.random()
                    < base_probability
                    else 0
                )

                extra_lambda = (
                    base_probability
                    * (multiplier - 1.0)
                )

                extra_count = self._poisson(
                    extra_lambda,
                    self.arrival_rng,
                )

                daily_count = (
                    base_count
                    + extra_count
                )

            for _ in range(daily_count):

                arrival = self._random_time_in_window(
                    day,
                    CLOTHES_ARRIVAL_WINDOW[
                        "start_hour"
                    ],
                    CLOTHES_ARRIVAL_WINDOW[
                        "end_hour"
                    ],
                )

                tasks.append(
                    self._new_task(
                        task_type=TASK_CLOTHES,
                        source=source,
                        destination=CLOTHES_DESTINATION,
                        arrival_time_s=arrival,
                    )
                )

        return tasks

    # ============================================================
    # Medication Delivery
    # ============================================================

    def _generate_medication(
        self,
        day: int,
    ) -> List[GeneratedTask]:

        tasks: List[GeneratedTask] = []

        total_expected = (
            NORMAL_WORKLOAD_PER_DAY[
                TASK_MEDICATION
            ]
            * self.workload_multiplier
        )

        scheduled_expected = (
            total_expected
            * MEDICATION_SCHEDULED_FRACTION
        )

        on_demand_expected = (
            total_expected
            - scheduled_expected
        )

        # --------------------------------------------------------
        # Scheduled medication
        # --------------------------------------------------------

        # Example:
        # expected 11 scheduled tasks/day
        # distributed across 4 scheduled medication windows.
        expected_per_window = (
            scheduled_expected
            / len(
                MEDICATION_SCHEDULED_BASE_HOURS
            )
        )

        for base_hour in (
            MEDICATION_SCHEDULED_BASE_HOURS
        ):

            task_count = self._poisson(
                expected_per_window,
                self.arrival_rng,
            )

            for _ in range(task_count):

                jitter_s = self.arrival_rng.uniform(
                    -MEDICATION_SCHEDULED_JITTER_MINUTES
                    * 60.0,
                    MEDICATION_SCHEDULED_JITTER_MINUTES
                    * 60.0,
                )

                arrival = (
                    self._day_offset(day)
                    + base_hour * 3600.0
                    + jitter_s
                )

                destination = (
                    self.arrival_rng.choice(
                        MEDICATION_DESTINATIONS
                    )
                )

                tasks.append(
                    self._new_task(
                        task_type=TASK_MEDICATION,
                        source=MEDICATION_SOURCE,
                        destination=destination,
                        arrival_time_s=arrival,
                    )
                )

        # --------------------------------------------------------
        # On-demand medication
        # --------------------------------------------------------

        self._validate_weights(
            MEDICATION_ON_DEMAND_TIME_WEIGHTS
        )

        for (
            start_hour,
            end_hour
        ), weight in (
            MEDICATION_ON_DEMAND_TIME_WEIGHTS.items()
        ):

            # Piecewise Poisson process:
            # each time block gets its own expected arrival count.
            lam_block = (
                on_demand_expected
                * weight
            )

            task_count = self._poisson(
                lam_block,
                self.arrival_rng,
            )

            for _ in range(task_count):

                arrival = self._random_time_in_window(
                    day,
                    start_hour,
                    end_hour,
                )

                destination = (
                    self.arrival_rng.choice(
                        MEDICATION_DESTINATIONS
                    )
                )

                tasks.append(
                    self._new_task(
                        task_type=TASK_MEDICATION,
                        source=MEDICATION_SOURCE,
                        destination=destination,
                        arrival_time_s=arrival,
                    )
                )

        return tasks

    # ============================================================
    # Specimen / Laboratory Delivery
    # ============================================================

    def _generate_specimen(
        self,
        day: int,
    ) -> List[GeneratedTask]:

        tasks: List[GeneratedTask] = []

        total_expected = (
            NORMAL_WORKLOAD_PER_DAY[
                TASK_SPECIMEN
            ]
            * self.workload_multiplier
        )

        self._validate_weights(
            SPECIMEN_TIME_WEIGHTS
        )

        # Piecewise NHPP approximation.
        #
        # Each time block gets:
        #
        #     N_block ~ Poisson(
        #         daily_expected × block_weight
        #     )
        #
        # Arrival timestamps are uniformly sampled
        # inside that block.
        for (
            start_hour,
            end_hour
        ), weight in (
            SPECIMEN_TIME_WEIGHTS.items()
        ):

            lam_block = (
                total_expected
                * weight
            )

            task_count = self._poisson(
                lam_block,
                self.arrival_rng,
            )

            for _ in range(task_count):

                arrival = self._random_time_in_window(
                    day,
                    start_hour,
                    end_hour,
                )

                clinical_location = (
                    self.arrival_rng.choice(
                        SPECIMEN_CLINICAL_LOCATIONS
                    )
                )

                # Bidirectional laboratory logistics.
                if (
                    self.arrival_rng.random()
                    < SPECIMEN_CLINICAL_TO_LAB_PROBABILITY
                ):
                    source = clinical_location
                    destination = SPECIMEN_LAB

                else:
                    source = SPECIMEN_LAB
                    destination = clinical_location

                tasks.append(
                    self._new_task(
                        task_type=TASK_SPECIMEN,
                        source=source,
                        destination=destination,
                        arrival_time_s=arrival,
                    )
                )

        return tasks

    # ============================================================
    # Ward Service
    # ============================================================

    def _generate_ward(
        self,
        day: int,
    ) -> List[GeneratedTask]:

        tasks: List[GeneratedTask] = []

        multiplier = (
            self.workload_multiplier
        )

        for destination in WARD_DESTINATIONS:

            for base_hour in WARD_BASE_HOURS:

                # -----------------------------------------------
                # Number of tasks around this scheduled slot
                # -----------------------------------------------

                if multiplier == 1.0:

                    task_count = 1

                elif multiplier < 1.0:

                    task_count = (
                        1
                        if self.arrival_rng.random()
                        < multiplier
                        else 0
                    )

                else:

                    # Keep the routine task.
                    task_count = 1

                    # Additional demand under heavier workload.
                    task_count += self._poisson(
                        multiplier - 1.0,
                        self.arrival_rng,
                    )

                # -----------------------------------------------
                # Generate tasks
                # -----------------------------------------------

                for _ in range(task_count):

                    jitter_s = (
                        self.arrival_rng.uniform(
                            -WARD_JITTER_MINUTES
                            * 60.0,
                            WARD_JITTER_MINUTES
                            * 60.0,
                        )
                    )

                    arrival = (
                        self._day_offset(day)
                        + base_hour * 3600.0
                        + jitter_s
                    )

                    tasks.append(
                        self._new_task(
                            task_type=TASK_WARD,
                            source=WARD_SOURCE,
                            destination=destination,
                            arrival_time_s=arrival,
                        )
                    )

        return tasks


# ============================================================
# Debug / manual run
# ============================================================

if __name__ == "__main__":

    generator = NormalTaskGenerator(
        seed=42
    )

    tasks = generator.generate()

    print(
        "Generated tasks:",
        len(tasks),
    )

    counts = {}

    for task in tasks:
        counts[task.task_type] = (
            counts.get(
                task.task_type,
                0,
            )
            + 1
        )

    print(
        "7-day counts:",
        counts,
    )

    print(
        "\nAverage tasks/day:"
    )

    for task_type, count in counts.items():
        print(
            f"{task_type}: "
            f"{count / SIMULATION_DAYS:.2f}"
        )

    print(
        "\nOverall average/day:",
        len(tasks) / SIMULATION_DAYS,
    )

    print(
        "\nFirst 20 tasks:"
    )

    for task in tasks[:20]:

        day = (
            int(
                task.arrival_time_s
                // SECONDS_PER_DAY
            )
            + 1
        )

        time_in_day = (
            task.arrival_time_s
            % SECONDS_PER_DAY
        )

        hour = int(
            time_in_day // 3600
        )

        minute = int(
            (
                time_in_day % 3600
            )
            // 60
        )

        second = int(
            time_in_day % 60
        )

        print(
            task.task_id,
            f"day={day}",
            f"{hour:02d}:"
            f"{minute:02d}:"
            f"{second:02d}",
            task.task_type,
            task.source,
            "->",
            task.destination,
            f"service="
            f"{task.service_time_s:.1f}s",
        )

    print("\nPriority counts:")

    priority_counts = {}

    for task in tasks:
        priority_counts[
            task.priority
        ] = (
            priority_counts.get(
                task.priority,
                0,
            )
            + 1
        )

    for priority in sorted(
        priority_counts
    ):
        print(
            f"priority={priority}:",
            priority_counts[priority],
        )