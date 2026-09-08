#!/usr/bin/env python3

import os
import statistics

from sb3_contrib import (
    MaskablePPO,
)

from experiment.generate_tasks import (
    generate_random_scenario,
)

from experiment.experiment_config import (
    BATTERY_PROFILE,
    CAPABILITY_PROFILE,
    ROBOT_SPEED,
    SERVICE_TIME,
)

from experiment.simulator import (
    BaselineSimulator,
)

from scheduler.task_selection.priority_scheduler import (
    PriorityScheduler,
)

from scheduler.robot_selection.nearest_scheduler import (
    NearestScheduler,
)

from scheduler.robot_selection.rule_based_scheduler import (
    RuleBasedScheduler,
)

from rl.hospital_gym_env import (
    HospitalGymEnv,
)


# ==========================================================
# Config
# ==========================================================

SEEDS = list(
    range(10)
)

TASK_COUNT = 20

LOAD = "medium"


# ==========================================================
# PPO Model Path
# ==========================================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

RL_DIR = os.path.join(
    os.path.dirname(
        SCRIPT_DIR
    ),
    "rl",
)

MODEL_V3_50K_PATH = os.path.join(
    RL_DIR,
    "models",
    "maskable_ppo_hospital_33d_reward_v3_50k.zip",
)

MODEL_V3_100K_PATH = os.path.join(
    RL_DIR,
    "models",
    "maskable_ppo_hospital_33d_reward_v3_100k.zip",
)


# ==========================================================
# Mean / Std Helper
# ==========================================================

def mean_std(
    values,
):

    values = [
        value
        for value
        in values
        if value is not None
    ]

    if not values:

        return (
            None,
            None,
        )

    mean_value = (
        statistics.mean(
            values
        )
    )

    std_value = (
        statistics.stdev(
            values
        )
        if len(values) >= 2
        else 0.0
    )

    return (
        mean_value,
        std_value,
    )


# ==========================================================
# Execution Record Success Helper
#
# Baseline 的 TaskExecutionRecord
# 可能具有 success 欄位。
#
# RL 的 RLTaskExecutionRecord
# 不一定具有 success 欄位。
#
# 因此：
#
# 1. 如果有 success：
#       success 必須為 True
#
# 2. 如果沒有 success：
#       預設視為 True
#
# 3. start_time / completion_time
#       必須存在
# ==========================================================

def is_successful_record(
    record,
):

    success = getattr(
        record,
        "success",
        True,
    )

    start_time = getattr(
        record,
        "start_time",
        None,
    )

    completion_time = getattr(
        record,
        "completion_time",
        None,
    )

    return (
        bool(
            success
        )
        and
        start_time is not None
        and
        completion_time is not None
    )


# ==========================================================
# Metrics From Final Execution Records
# ==========================================================

def calculate_metrics(
    execution_records,
    robot_states,
    simulation_end_time,
):

    # ======================================================
    # Successful Records
    # ======================================================

    successful_records = [

        record

        for record
        in execution_records

        if is_successful_record(
            record
        )
    ]

    if not successful_records:

        raise RuntimeError(
            "No successful execution records."
        )

    # ======================================================
    # Waiting Time
    # ======================================================

    waiting_times = [

        record.waiting_time

        for record
        in successful_records
    ]

    # ======================================================
    # Completion Time
    #
    # completion_time - arrival_time
    # ======================================================

    completion_times = [

        (
            record.completion_time
            -
            record.arrival_time
        )

        for record
        in successful_records
    ]

    # ======================================================
    # Emergency Waiting
    #
    # Priority = 3
    # ======================================================

    emergency_waiting_times = [

        record.waiting_time

        for record
        in successful_records

        if record.priority == 3
    ]

    # ======================================================
    # High Priority Waiting
    #
    # Priority = 2
    # ======================================================

    high_waiting_times = [

        record.waiting_time

        for record
        in successful_records

        if record.priority == 2
    ]

    # ======================================================
    # Travel Distance
    # ======================================================

    total_travel_distance = sum(

        record.travel_distance

        for record
        in successful_records
    )

    # ======================================================
    # Robot Task Counts
    # ======================================================

    robot_task_counts = {

        robot_id: 0

        for robot_id
        in robot_states
    }

    for record in (
        successful_records
    ):

        if (
            record.robot_id
            not in robot_task_counts
        ):

            robot_task_counts[
                record.robot_id
            ] = 0

        robot_task_counts[
            record.robot_id
        ] += 1

    # ======================================================
    # Robot Utilization
    # ======================================================

    robot_utilizations = []

    for sim_state in (
        robot_states.values()
    ):

        if simulation_end_time > 0.0:

            utilization = (

                sim_state.total_busy_time
                /
                simulation_end_time
            )

        else:

            utilization = 0.0

        robot_utilizations.append(
            utilization
        )

    # ======================================================
    # Success Rate
    # ======================================================

    success_rate = (

        len(
            successful_records
        )
        /
        TASK_COUNT
    )

    # ======================================================
    # Return
    # ======================================================

    return {

        "average_waiting_time":
            statistics.mean(
                waiting_times
            ),

        "average_completion_time":
            statistics.mean(
                completion_times
            ),

        "emergency_waiting_time":
            (
                statistics.mean(
                    emergency_waiting_times
                )
                if emergency_waiting_times
                else None
            ),

        "high_waiting_time":
            (
                statistics.mean(
                    high_waiting_times
                )
                if high_waiting_times
                else None
            ),

        "total_travel_distance":
            total_travel_distance,

        "makespan":
            simulation_end_time,

        "average_utilization":
            statistics.mean(
                robot_utilizations
            ),

        "task_load_std":
            statistics.pstdev(
                robot_task_counts.values()
            ),

        "success_rate":
            success_rate,
    }


# ==========================================================
# Create Baseline Robot Scheduler
# ==========================================================

def create_robot_scheduler(
    scheduler_name,
    waypoints,
):

    if (
        scheduler_name
        ==
        "nearest"
    ):

        return (
            NearestScheduler(
                waypoints
            )
        )

    if (
        scheduler_name
        ==
        "rule_based"
    ):

        return (
            RuleBasedScheduler(
                waypoints
            )
        )

    raise ValueError(
        "Unknown robot scheduler: "
        f"{scheduler_name}"
    )


# ==========================================================
# Run One Baseline Episode
# ==========================================================

def run_baseline_episode(
    seed,
    robot_scheduler_name,
):

    # ======================================================
    # Scenario
    # ======================================================

    scenario = (
        generate_random_scenario(

            task_count=TASK_COUNT,

            seed=seed,

            load=LOAD,

            battery_profile=(
                BATTERY_PROFILE
            ),

            capability_profile=(
                CAPABILITY_PROFILE
            ),
        )
    )

    # ======================================================
    # Robot Scheduler
    #
    # 使用該 Scenario 的 Waypoints。
    # ======================================================

    robot_scheduler = (
        create_robot_scheduler(

            scheduler_name=(
                robot_scheduler_name
            ),

            waypoints=(
                scenario.waypoints
            ),
        )
    )

    # ======================================================
    # Baseline Simulator
    #
    # Task Selection：
    #
    # PriorityScheduler
    #
    # Robot Selection：
    #
    # Nearest
    # 或
    # Rule-based
    # ======================================================

    simulator = BaselineSimulator(

        scenario=scenario,

        task_scheduler=(
            PriorityScheduler()
        ),

        robot_scheduler=(
            robot_scheduler
        ),

        robot_speed=(
            ROBOT_SPEED
        ),

        service_time=(
            SERVICE_TIME
        ),
    )

    # ======================================================
    # Run
    # ======================================================

    result = (
        simulator.run()
    )

    # ======================================================
    # Final Execution Records
    #
    # BaselineSimulator.run()
    # 目前使用：
    #
    # result["records"]
    # result["simulation_end_time"]
    # ======================================================

    execution_records = (
        result[
            "records"
        ]
    )

    simulation_end_time = (
        result[
            "simulation_end_time"
        ]
    )

    # ======================================================
    # Metrics
    # ======================================================

    return (
        calculate_metrics(

            execution_records=(
                execution_records
            ),

            robot_states=(
                simulator.robot_states
            ),

            simulation_end_time=(
                simulation_end_time
            ),
        )
    )


# ==========================================================
# Run One RL Episode
# ==========================================================

def run_rl_episode(
    model,
    seed,
):

    # ======================================================
    # Scenario
    #
    # 與 Baseline 使用相同：
    #
    # task_count
    # seed
    # load
    # battery profile
    # capability profile
    # ======================================================

    scenario = (
        generate_random_scenario(

            task_count=TASK_COUNT,

            seed=seed,

            load=LOAD,

            battery_profile=(
                BATTERY_PROFILE
            ),

            capability_profile=(
                CAPABILITY_PROFILE
            ),
        )
    )

    # ======================================================
    # Environment
    # ======================================================

    env = HospitalGymEnv(

        scenario=scenario,

        robot_speed=(
            ROBOT_SPEED
        ),

        service_time=(
            SERVICE_TIME
        ),
    )

    (
        observation,
        info,
    ) = (
        env.reset()
    )

    # ======================================================
    # PPO Episode
    # ======================================================

    while True:

        # --------------------------------------------------
        # Capability Action Mask
        # --------------------------------------------------

        mask = (
            env.action_masks()
        )

        # --------------------------------------------------
        # PPO Robot Selection
        # --------------------------------------------------

        (
            action,
            _
        ) = (
            model.predict(

                observation,

                action_masks=mask,

                deterministic=True,
            )
        )

        # --------------------------------------------------
        # Environment Step
        # --------------------------------------------------

        (
            observation,
            reward,
            terminated,
            truncated,
            info,
        ) = (
            env.step(
                action
            )
        )

        if (
            terminated
            or truncated
        ):

            break

    # ======================================================
    # Final Execution Records
    #
    # 注意：
    #
    # RL step()
    # 只做 Assignment。
    #
    # 真正：
    #
    # waiting_time
    # start_time
    # completion_time
    # travel_distance
    #
    # 都從 execution_records 取得。
    # ======================================================

    execution_records = (
        env.core_env
        .execution_records
    )

    simulation_end_time = (
        env.core_env
        .get_simulation_end_time()
    )

    # ======================================================
    # Metrics
    # ======================================================

    metrics = (
        calculate_metrics(

            execution_records=(
                execution_records
            ),

            robot_states=(
                env.core_env
                .robot_states
            ),

            simulation_end_time=(
                simulation_end_time
            ),
        )
    )

    env.close()

    return (
        metrics
    )


# ==========================================================
# Print Summary
# ==========================================================

def print_summary(
    method_name,
    results,
):

    print()

    print("=" * 110)

    print(
        method_name
    )

    print("=" * 110)

    metrics = [

        "average_waiting_time",

        "average_completion_time",

        "emergency_waiting_time",

        "high_waiting_time",

        "total_travel_distance",

        "makespan",

        "average_utilization",

        "task_load_std",

        "success_rate",
    ]

    summary = {}

    for metric in (
        metrics
    ):

        (
            mean_value,
            std_value,
        ) = (
            mean_std(

                [
                    result[
                        metric
                    ]

                    for result
                    in results
                ]
            )
        )

        summary[
            metric
        ] = (
            mean_value,
            std_value,
        )

        if mean_value is None:

            print(
                f"{metric:<28}"
                "N/A"
            )

        else:

            print(
                f"{metric:<28}"
                f"{mean_value:.3f}"
                f" ± "
                f"{std_value:.3f}"
            )

    return (
        summary
    )


# ==========================================================
# Format Value
# ==========================================================

def format_value(
    value,
):

    if value is None:

        return (
            "N/A"
        )

    return (
        f"{value:.3f}"
    )


# ==========================================================
# Main
# ==========================================================

def main():

    print("=" * 110)

    print(
        "PRIORITY SCHEDULER FAIR COMPARISON"
    )

    print("=" * 110)

    print(
        "Task Count:",
        TASK_COUNT,
    )

    print(
        "Load:",
        LOAD,
    )

    print(
        "Seeds:",
        SEEDS,
    )

    print(
        "Battery Profile:",
        BATTERY_PROFILE,
    )

    print(
        "Capability Profile:",
        CAPABILITY_PROFILE,
    )

    print(
        "RL Model V3 50K:",
        MODEL_V3_50K_PATH,
    )

    print(
        "RL Model V3 100K:",
        MODEL_V3_100K_PATH,
    )

    print()

    # ======================================================
    # PPO Model Check
    # ======================================================

    for model_path in (
        MODEL_V3_50K_PATH,
        MODEL_V3_100K_PATH,
    ):

        if not os.path.exists(
            model_path
        ):

            raise FileNotFoundError(
                "RL model not found: "
                f"{model_path}"
            )

    # ======================================================
    # Load PPO
    # ======================================================

    model_v3_50k = MaskablePPO.load(
        MODEL_V3_50K_PATH,
        device="cpu",
    )

    model_v3_100k = MaskablePPO.load(
        MODEL_V3_100K_PATH,
        device="cpu",
    )

    nearest_results = []
    rule_results = []

    rl_v3_50k_results = []
    rl_v3_100k_results = []

    # ======================================================
    # Fair Comparison
    #
    # 每一個 Seed：
    #
    # Priority + Nearest
    #
    # Priority + Rule-based
    #
    # Priority + PPO
    #
    # 都使用同一組 Scenario 設定。
    # ======================================================

    for seed in (
        SEEDS
    ):

        # --------------------------------------------------
        # Priority + Nearest
        # --------------------------------------------------

        nearest = (
            run_baseline_episode(

                seed=seed,

                robot_scheduler_name=(
                    "nearest"
                ),
            )
        )

        # --------------------------------------------------
        # Priority + Rule-based
        # --------------------------------------------------

        rule = (
            run_baseline_episode(

                seed=seed,

                robot_scheduler_name=(
                    "rule_based"
                ),
            )
        )

        # --------------------------------------------------
        # Priority + PPO
        # --------------------------------------------------

        rl_v3_50k = (
            run_rl_episode(

                model=model_v3_50k,

                seed=seed,
            )
        )

        rl_v3_100k = (
            run_rl_episode(

                model=model_v3_100k,

                seed=seed,
            )
        )

        nearest_results.append(
            nearest
        )

        rule_results.append(
            rule
        )

        rl_v3_50k_results.append(
            rl_v3_50k
        )

        rl_v3_100k_results.append(
            rl_v3_100k
        )

        # --------------------------------------------------
        # Seed Result
        # --------------------------------------------------

        print(
            f"Seed {seed:02d}"

            f" | Near="
            f"{nearest['average_waiting_time']:.2f}"

            f" | Rule="
            f"{rule['average_waiting_time']:.2f}"

            f" | PPO-50k="
            f"{rl_v3_50k['average_waiting_time']:.2f}"

            f" | PPO-100k="
            f"{rl_v3_100k['average_waiting_time']:.2f}"
        )

    # ======================================================
    # Detailed Summary
    # ======================================================

    nearest_summary = (
        print_summary(

            "PRIORITY + NEAREST",

            nearest_results,
        )
    )

    rule_summary = (
        print_summary(

            "PRIORITY + RULE-BASED",

            rule_results,
        )
    )

    rl_v3_50k_summary = (
        print_summary(

            "PRIORITY + PPO 33D REWARD V3 50K",

            rl_v3_50k_results,
        )
    )

    rl_v3_100k_summary = (
        print_summary(

            "PRIORITY + PPO 33D REWARD V3 100K",

            rl_v3_100k_results,
        )
    )

    # ======================================================
    # Compact Comparison
    # ======================================================

    print()

    print("=" * 110)

    print(
        "COMPACT COMPARISON"
    )

    print("=" * 110)

    metrics = [

        "average_waiting_time",

        "average_completion_time",

        "emergency_waiting_time",

        "high_waiting_time",

        "total_travel_distance",

        "makespan",

        "average_utilization",

        "task_load_std",

        "success_rate",
    ]

    print(
        f"{'Metric':<30}"
        f"{'Nearest':>14}"
        f"{'Rule':>14}"
        f"{'PPO-50k':>14}"
        f"{'PPO-100k':>14}"
    )

    print(
        "-" * 86
    )

    for metric in (
        metrics
    ):

        nearest_mean = (
            nearest_summary[
                metric
            ][0]
        )

        rule_mean = (
            rule_summary[
                metric
            ][0]
        )

        rl_v3_50k_mean = (
            rl_v3_50k_summary[
                metric
            ][0]
        )

        rl_v3_100k_mean = (
            rl_v3_100k_summary[
                metric
            ][0]
        )

        print(
            f"{metric:<30}"
            f"{format_value(nearest_mean):>14}"
            f"{format_value(rule_mean):>14}"
            f"{format_value(rl_v3_50k_mean):>14}"
            f"{format_value(rl_v3_100k_mean):>14}"
        )

    print()

    print(
        "FAIR COMPARISON COMPLETED"
    )


if __name__ == "__main__":

    main()