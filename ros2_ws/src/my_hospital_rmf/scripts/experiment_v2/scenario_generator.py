#!/usr/bin/env python3

import random

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
)

from experiment_v2.models import (
    SimulationScenario,
)


# ==========================================================
# Hospital Places
# ==========================================================

def create_hospital_places(
) -> dict[str, Place]:
    """
    Algorithm-level Simulator 使用的 Hospital Layout。

    目前先使用固定 2D 座標，
    讓所有 Baseline 使用完全相同的距離環境。

    後續 RMF system-level experiment
    再替換成實際 Nav Graph / path distance。
    """

    return {
        "reception": Place(
            "reception",
            0.0,
            0.0,
            "L1",
        ),

        "nurse_station": Place(
            "nurse_station",
            12.0,
            10.0,
            "L1",
        ),

        "pharmacy": Place(
            "pharmacy",
            0.0,
            20.0,
            "L1",
        ),

        "lab": Place(
            "lab",
            25.0,
            20.0,
            "L1",
        ),

        "waiting_a": Place(
            "waiting_a",
            5.0,
            5.0,
            "L1",
        ),

        "waiting_b": Place(
            "waiting_b",
            20.0,
            5.0,
            "L1",
        ),

        "ward_a": Place(
            "ward_a",
            35.0,
            5.0,
            "L1",
        ),

        "ward_b": Place(
            "ward_b",
            35.0,
            15.0,
            "L1",
        ),

        "ward_c": Place(
            "ward_c",
            35.0,
            25.0,
            "L1",
        ),

        "ward_d": Place(
            "ward_d",
            35.0,
            35.0,
            "L1",
        ),

        "storage": Place(
            "storage",
            10.0,
            35.0,
            "L1",
        ),

        "charging_station": Place(
            "charging_station",
            0.0,
            35.0,
            "L1",
        ),
    }


# ==========================================================
# Robots
# ==========================================================

def create_hospital_robots(
    rng: random.Random,
) -> list[RobotState]:
    """
    建立異質 Robot Fleet。

    每台 Robot Capability 不完全相同，
    讓 Capability Matching 真正參與派工。
    """

    starting_places = [
        ("reception", 0.0, 0.0),
        ("nurse_station", 12.0, 10.0),
        ("lab", 25.0, 20.0),
        ("storage", 10.0, 35.0),
    ]

    batteries = [
        rng.uniform(
            0.55,
            1.00,
        )
        for _ in range(4)
    ]

    return [
        RobotState(
            robot_id="hospital_robot_1",
            fleet_name="hospital_fleet",
            status="idle",
            battery=batteries[0],
            x=starting_places[0][1],
            y=starting_places[0][2],
            map_name="L1",
            capabilities={
                "navigation",
                "medicine_delivery",
                "general_delivery",
            },
            available=True,
        ),

        RobotState(
            robot_id="hospital_robot_2",
            fleet_name="hospital_fleet",
            status="idle",
            battery=batteries[1],
            x=starting_places[1][1],
            y=starting_places[1][2],
            map_name="L1",
            capabilities={
                "navigation",
                "specimen_delivery",
                "general_delivery",
            },
            available=True,
        ),

        RobotState(
            robot_id="hospital_robot_3",
            fleet_name="hospital_fleet",
            status="idle",
            battery=batteries[2],
            x=starting_places[2][1],
            y=starting_places[2][2],
            map_name="L1",
            capabilities={
                "navigation",
                "general_delivery",
            },
            available=True,
        ),

        RobotState(
            robot_id="hospital_robot_4",
            fleet_name="hospital_fleet",
            status="idle",
            battery=batteries[3],
            x=starting_places[3][1],
            y=starting_places[3][2],
            map_name="L1",
            capabilities={
                "navigation",
                "medicine_delivery",
                "specimen_delivery",
                "general_delivery",
            },
            available=True,
        ),
    ]


# ==========================================================
# Priority
# ==========================================================

def generate_priority(
    rng: random.Random,
) -> int:
    """
    初始 Priority Distribution：

        Low       20%
        Normal    50%
        High      20%
        Emergency 10%

    目前為 Scenario 開發設定，
    正式 Experiment 前再固定。
    """

    return rng.choices(
        population=[
            0,
            1,
            2,
            3,
        ],
        weights=[
            0.20,
            0.50,
            0.20,
            0.10,
        ],
        k=1,
    )[0]


# ==========================================================
# Task
# ==========================================================

def create_random_task(
    task_index: int,
    created_at: float,
    rng: random.Random,
) -> Task:
    """
    產生一個 Hospital Task。
    """

    task_type = rng.choice(
        [
            "medicine_delivery",
            "specimen_delivery",
            "general_delivery",
            "waste_collection",
        ]
    )

    wards = [
        "ward_a",
        "ward_b",
        "ward_c",
        "ward_d",
    ]

    if task_type == "medicine_delivery":

        source = "pharmacy"

        destination = rng.choice(
            wards
        )

        capabilities = {
            "navigation",
            "medicine_delivery",
        }

    elif task_type == "specimen_delivery":

        source = rng.choice(
            wards
        )

        destination = "lab"

        capabilities = {
            "navigation",
            "specimen_delivery",
        }

    elif task_type == "general_delivery":

        source = "storage"

        destination = rng.choice(
            [
                "nurse_station",
                "waiting_a",
                "waiting_b",
                *wards,
            ]
        )

        capabilities = {
            "navigation",
            "general_delivery",
        }

    else:

        # Waste Collection
        source = rng.choice(
            wards
        )

        destination = "storage"

        capabilities = {
            "navigation",
            "general_delivery",
        }

    return Task(
        task_id=(
            f"T{task_index:04d}"
        ),
        task_type=task_type,
        source=source,
        destination=destination,
        priority=(
            generate_priority(
                rng
            )
        ),
        required_capabilities=(
            capabilities
        ),
        status="pending",
        assigned_robot=None,
        created_at=created_at,
    )


# ==========================================================
# Scenario Generator
# ==========================================================

def generate_hospital_scenario(
    seed: int,
    task_count: int = 50,
    mean_interarrival_seconds: float = 20.0,
    robot_speed_mps: float = 1.0,
    service_time_seconds: float = 30.0,
) -> SimulationScenario:
    """
    依指定 seed 建立可重現的 Hospital Scenario。

    Arrival 使用 exponential inter-arrival time，
    模擬任務不是固定週期出現。
    """

    if task_count < 0:

        raise ValueError(
            "task_count cannot be negative"
        )

    if mean_interarrival_seconds <= 0.0:

        raise ValueError(
            "mean_interarrival_seconds "
            "must be greater than 0"
        )

    rng = random.Random(
        seed
    )

    places = (
        create_hospital_places()
    )

    robots = (
        create_hospital_robots(
            rng=rng
        )
    )

    tasks = []

    current_arrival_time = 0.0

    for index in range(
        1,
        task_count + 1,
    ):

        # 第一個 Task 固定 t=0，
        # 之後才加入 inter-arrival。
        if index > 1:

            current_arrival_time += (
                rng.expovariate(
                    1.0
                    /
                    mean_interarrival_seconds
                )
            )

        task = (
            create_random_task(
                task_index=index,
                created_at=(
                    current_arrival_time
                ),
                rng=rng,
            )
        )

        tasks.append(
            task
        )

    return SimulationScenario(
        name=(
            f"hospital_seed_{seed}"
        ),
        tasks=tasks,
        robots=robots,
        places=places,
        robot_speed_mps=(
            robot_speed_mps
        ),
        service_time_seconds=(
            service_time_seconds
        ),
    )