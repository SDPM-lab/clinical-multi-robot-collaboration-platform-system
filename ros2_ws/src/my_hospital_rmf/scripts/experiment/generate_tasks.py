#!/usr/bin/env python3

import random

from experiment.scenarios import (
    Scenario,
    BASE_WAYPOINTS,
    create_robot,
    create_task,
)


LOAD_PROFILES = {

    "low": {
        "min_interarrival": 15.0,
        "max_interarrival": 30.0,
    },

    "medium": {
        "min_interarrival": 8.0,
        "max_interarrival": 15.0,
    },

    "high": {
        "min_interarrival": 2.0,
        "max_interarrival": 8.0,
    },
}

BATTERY_PROFILES = {

    "normal": {
        "min_battery": 0.60,
        "max_battery": 1.00,
    },

    "mixed": {
        "min_battery": 0.10,
        "max_battery": 1.00,
    },

    "stress": {
        "min_battery": 0.10,
        "max_battery": 1.00,
    },
}

CAPABILITY_PROFILES = {

    "heterogeneous": {

        "robot_1": {
            "navigation",
            "medicine_delivery",
            "general_delivery",
        },

        "robot_2": {
            "navigation",
            "specimen_delivery",
            "general_delivery",
        },

        "robot_3": {
            "navigation",
            "general_delivery",
            "manipulation",
        },
    },

    "competitive": {

        "robot_1": {
            "navigation",
            "medicine_delivery",
            "general_delivery",
        },

        "robot_2": {
            "navigation",
            "medicine_delivery",
            "specimen_delivery",
            "general_delivery",
        },

        "robot_3": {
            "navigation",
            "specimen_delivery",
            "general_delivery",
            "manipulation",
        },
    },
}

# ==========================================================
# Random Task Generator
# ==========================================================

def generate_random_scenario(
    task_count: int = 20,
    seed: int = 42,
    load: str = "medium",
    battery_profile: str = "normal",
    capability_profile: str = "heterogeneous",
) -> Scenario:
    """
    產生可重現的隨機 Task Scenario。

    task_count:
        Task 數量

    seed:
        Random Seed。
        相同 seed 必須產生相同 Scenario。

    load:
        Task Load。
        "low"、"medium" 或 "high"。

    battery_profile:
        Robot 初始 Battery Profile。
        "normal"、"mixed" 或 "stress"。
    """

    if task_count <= 0:
        raise ValueError(
            "task_count must be > 0"
        )

    if load not in LOAD_PROFILES:

        raise ValueError(
            "Unknown load profile: "
            f"{load}. "
            "Available profiles: "
            + ", ".join(
                LOAD_PROFILES.keys()
            )
        )

    load_profile = (
        LOAD_PROFILES[
            load
        ]
    )

    min_interarrival = (
        load_profile[
            "min_interarrival"
        ]
    )

    max_interarrival = (
        load_profile[
            "max_interarrival"
        ]
    )

    if battery_profile not in BATTERY_PROFILES:

        raise ValueError(
            "Unknown battery profile: "
            f"{battery_profile}. "
            "Available profiles: "
            + ", ".join(
                BATTERY_PROFILES.keys()
            )
        )

        battery_config = (
            BATTERY_PROFILES[
                battery_profile
            ]
        )

        min_battery = (
            battery_config[
                "min_battery"
            ]
        )

        max_battery = (
            battery_config[
                "max_battery"
            ]
        )

    if capability_profile not in CAPABILITY_PROFILES:

        raise ValueError(
            "Unknown capability profile: "
            f"{capability_profile}. "
            "Available profiles: "
            + ", ".join(
                CAPABILITY_PROFILES.keys()
            )
        )

    robot_capabilities = (
        CAPABILITY_PROFILES[
            capability_profile
        ]
    )


    # ------------------------------------------------------
    # 使用獨立 Random Instance
    #
    # 必須先建立 rng，
    # 後面的 Battery 與 Task 都使用同一個 seed。
    # ------------------------------------------------------

    rng = random.Random(
        seed
    )

    if battery_profile == "stress":

        low_battery_robot_index = (
            rng.randrange(
                3
            )
        )

        robot_batteries = []

        for index in range(3):

            if (
                index
                == low_battery_robot_index
            ):

                battery = rng.uniform(
                    0.10,
                    0.19,
                )

            else:

                battery = rng.uniform(
                    0.60,
                    1.00,
                )

            robot_batteries.append(
                battery
            )

    else:

        robot_batteries = [

            rng.uniform(
                min_battery,
                max_battery,
            )

            for _ in range(3)
        ]

    # ======================================================
    # Robot 初始狀態
    #
    # 第一版 Robot 保持固定，
    # 只隨機產生 Task。
    # ======================================================

    robots = [

        create_robot(
            robot_id="robot_1",
            x=3.0,
            y=0.0,
            battery=robot_batteries[0],
            capabilities=(
                robot_capabilities[
                    "robot_1"
                ]
            ),
        ),

        create_robot(
            robot_id="robot_2",
            x=12.0,
            y=0.0,
            battery=robot_batteries[1],
            capabilities=(
                robot_capabilities[
                    "robot_2"
                ]
            ),
        ),

        create_robot(
            robot_id="robot_3",
            x=5.0,
            y=12.0,
            battery=robot_batteries[2],
            capabilities=(
                robot_capabilities[
                    "robot_3"
                ]
            ),
        ),
    ]

    # ======================================================
    # Task Type Config
    # ======================================================

    task_configs = {

        "medicine_delivery": {

            "source":
                "pharmacy",

            "destinations": [
                "ward_a",
                "ward_b",
                "ward_c",
            ],

            "required_capabilities": [
                "navigation",
                "medicine_delivery",
            ],
        },

        "specimen_delivery": {

            "sources": [
                "ward_a",
                "ward_b",
                "ward_c",
            ],

            "destination":
                "lab",

            "required_capabilities": [
                "navigation",
                "specimen_delivery",
            ],
        },

        "general_delivery": {

            "source":
                "storage",

            "destinations": [
                "nurse_station",
                "ward_a",
                "ward_b",
                "ward_c",
            ],

            "required_capabilities": [
                "navigation",
                "general_delivery",
            ],
        },
    }

    task_types = [
        "medicine_delivery",
        "specimen_delivery",
        "general_delivery",
    ]

    # ------------------------------------------------------
    # Task Type 分布
    #
    # medicine  40%
    # specimen  30%
    # general   30%
    # ------------------------------------------------------

    task_type_weights = [
        0.40,
        0.30,
        0.30,
    ]

    # ======================================================
    # Priority Distribution
    #
    # Low       10%
    # Normal    50%
    # High      30%
    # Emergency 10%
    # ======================================================

    priorities = [
        0,
        1,
        2,
        3,
    ]

    priority_weights = [
        0.10,
        0.50,
        0.30,
        0.10,
    ]

    tasks = []

    task_arrival_times = {}

    current_arrival_time = 0.0

    # ======================================================
    # Generate Tasks
    # ======================================================

    for index in range(
        task_count
    ):

        task_id = (
            f"T{index + 1:03d}"
        )

        # --------------------------------------------------
        # Task Type
        # --------------------------------------------------

        task_type = rng.choices(
            task_types,
            weights=task_type_weights,
            k=1,
        )[0]

        config = (
            task_configs[
                task_type
            ]
        )

        # --------------------------------------------------
        # Source / Destination
        # --------------------------------------------------

        if (
            task_type
            == "medicine_delivery"
        ):

            source = (
                config["source"]
            )

            destination = rng.choice(
                config[
                    "destinations"
                ]
            )

        elif (
            task_type
            == "specimen_delivery"
        ):

            source = rng.choice(
                config[
                    "sources"
                ]
            )

            destination = (
                config[
                    "destination"
                ]
            )

        elif (
            task_type
            == "general_delivery"
        ):

            source = (
                config["source"]
            )

            destination = rng.choice(
                config[
                    "destinations"
                ]
            )

        else:

            raise RuntimeError(
                "Unknown task type: "
                f"{task_type}"
            )

        # --------------------------------------------------
        # Priority
        # --------------------------------------------------

        priority = rng.choices(
            priorities,
            weights=priority_weights,
            k=1,
        )[0]

        # --------------------------------------------------
        # 建立 Task
        # --------------------------------------------------

        task = create_task(

            task_id=task_id,

            task_type=task_type,

            source=source,

            destination=destination,

            priority=priority,

            required_capabilities=(
                config[
                    "required_capabilities"
                ]
            ),
        )

        tasks.append(
            task
        )

        # --------------------------------------------------
        # Arrival Time
        #
        # T001 固定 time=0 到達。
        #
        # 後續 Task 根據 interarrival time
        # 依序進入系統。
        # --------------------------------------------------

        if index == 0:

            current_arrival_time = (
                0.0
            )

        else:

            interarrival_time = (
                rng.uniform(
                    min_interarrival,
                    max_interarrival,
                )
            )

            current_arrival_time += (
                interarrival_time
            )

        task_arrival_times[
            task_id
        ] = (
            current_arrival_time
        )

    # ======================================================
    # Scenario
    # ======================================================

    return Scenario(

        name=(
            f"random_"
            f"{task_count}_tasks_"
            f"{load}_load_"
            f"{battery_profile}_battery_"
            f"{capability_profile}_capability_"
            f"seed_{seed}"
        ),

        description=(
            f"隨機產生 {task_count} 筆 Task，"
            f"Load={load}，"
            f"Random Seed={seed}"
        ),

        waypoints=(
            BASE_WAYPOINTS.copy()
        ),

        robots=robots,

        tasks=tasks,

        task_arrival_times=(
            task_arrival_times
        ),
    )