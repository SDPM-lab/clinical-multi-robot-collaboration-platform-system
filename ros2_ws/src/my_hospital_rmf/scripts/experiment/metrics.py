#!/usr/bin/env python3

import math
import statistics


# ==========================================================
# Helper
# ==========================================================

def safe_mean(
    values,
):

    values = list(
        values
    )

    if not values:
        return 0.0

    return statistics.mean(
        values
    )


# ==========================================================
# Task Metrics
# ==========================================================

def calculate_task_metrics(
    records,
):

    successful = [
        record
        for record in records
        if record.success
    ]

    failed = [
        record
        for record in records
        if not record.success
    ]

    # ------------------------------------------------------
    # Waiting Time
    #
    # arrival → 開始執行
    # ------------------------------------------------------

    waiting_times = [

        record.waiting_time

        for record in successful

        if record.waiting_time
        is not None
    ]

    # ------------------------------------------------------
    # Completion / Flow Time
    #
    # arrival → 完成
    # ------------------------------------------------------

    completion_times = [

        (
            record.completion_time
            - record.arrival_time
        )

        for record in successful

        if (
            record.completion_time
            is not None
        )
    ]

    # ------------------------------------------------------
    # Service Time
    # ------------------------------------------------------

    service_times = [

        record.service_time

        for record in successful

        if record.service_time
        is not None
    ]

    # ------------------------------------------------------
    # Task Travel Distance
    # ------------------------------------------------------

    travel_distances = [

        record.travel_distance

        for record in successful

        if record.travel_distance
        is not None
    ]

    # ------------------------------------------------------
    # Priority-specific waiting time
    #
    # 0 Low
    # 1 Normal
    # 2 High
    # 3 Emergency
    # ------------------------------------------------------

    priority_waiting = {}

    for priority in range(
        4
    ):

        values = [

            record.waiting_time

            for record in successful

            if (
                record.priority
                == priority
                and record.waiting_time
                is not None
            )
        ]

        if values:

            priority_waiting[
                priority
            ] = statistics.mean(
                values
            )

        else:

            priority_waiting[
                priority
            ] = None

    # ------------------------------------------------------
    # Success Rate
    # ------------------------------------------------------

    total_tasks = len(
        records
    )

    successful_tasks = len(
        successful
    )

    failed_tasks = len(
        failed
    )

    success_rate = (
        successful_tasks
        / total_tasks
        if total_tasks > 0
        else 0.0
    )

    return {

        "total_tasks":
            total_tasks,

        "successful_tasks":
            successful_tasks,

        "failed_tasks":
            failed_tasks,

        "success_rate":
            success_rate,

        "average_waiting_time":
            safe_mean(
                waiting_times
            ),

        "average_completion_time":
            safe_mean(
                completion_times
            ),

        "average_service_time":
            safe_mean(
                service_times
            ),

        "total_travel_distance":
            sum(
                travel_distances
            ),

        "average_travel_distance":
            safe_mean(
                travel_distances
            ),

        "priority_waiting_time":
            priority_waiting,
    }


# ==========================================================
# Robot Metrics
# ==========================================================

def calculate_robot_metrics(
    robot_states,
    simulation_end_time,
):

    robot_metrics = {}

    task_counts = []

    utilizations = []

    total_robot_distance = 0.0
    total_robot_busy_time = 0.0

    for (
        robot_id,
        sim_state,
    ) in robot_states.items():

        # --------------------------------------------------
        # Utilization
        #
        # busy time / simulation time
        # --------------------------------------------------

        if (
            simulation_end_time
            > 0
        ):

            utilization = (
                sim_state.total_busy_time
                / simulation_end_time
            )

        else:

            utilization = 0.0

        task_counts.append(
            sim_state.completed_tasks
        )

        utilizations.append(
            utilization
        )

        total_robot_distance += (
            sim_state.total_distance
        )

        total_robot_busy_time += (
            sim_state.total_busy_time
        )

        robot_metrics[
            robot_id
        ] = {

            "completed_tasks":
                sim_state.completed_tasks,

            "total_distance":
                sim_state.total_distance,

            "total_busy_time":
                sim_state.total_busy_time,

            "utilization":
                utilization,
        }

    # ------------------------------------------------------
    # Load Balance
    #
    # 第一版使用 task count 的標準差。
    #
    # 越小代表分配越平均。
    # ------------------------------------------------------

    if len(
        task_counts
    ) >= 2:

        task_load_std = (
            statistics.pstdev(
                task_counts
            )
        )

    else:

        task_load_std = 0.0

    # ------------------------------------------------------
    # Utilization Standard Deviation
    #
    # 越小表示 Robot 利用率越平均。
    # ------------------------------------------------------

    if len(
        utilizations
    ) >= 2:

        utilization_std = (
            statistics.pstdev(
                utilizations
            )
        )

    else:

        utilization_std = 0.0

    return {

        "robots":
            robot_metrics,

        "total_robot_distance":
            total_robot_distance,

        "total_robot_busy_time":
            total_robot_busy_time,

        "average_robot_utilization":
            safe_mean(
                utilizations
            ),

        "task_load_std":
            task_load_std,

        "utilization_std":
            utilization_std,
    }


# ==========================================================
# Complete Metrics
# ==========================================================

def calculate_metrics(
    simulation_result,
):

    records = (
        simulation_result[
            "records"
        ]
    )

    robot_states = (
        simulation_result[
            "robots"
        ]
    )

    simulation_end_time = (
        simulation_result[
            "simulation_end_time"
        ]
    )

    task_metrics = (
        calculate_task_metrics(
            records
        )
    )

    robot_metrics = (
        calculate_robot_metrics(
            robot_states,
            simulation_end_time,
        )
    )

    return {

        "simulation_end_time":
            simulation_end_time,

        "task_metrics":
            task_metrics,

        "robot_metrics":
            robot_metrics,
    }