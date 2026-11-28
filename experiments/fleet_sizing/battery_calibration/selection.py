from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean, pstdev

from experiments.fleet_sizing.battery_calibration import (
    config as cfg,
)


# ============================================================
# Group and summarize experiment runs
# ============================================================

def summarize_runs(rows, parameter_fields):

    if not rows:
        raise ValueError("No experiment rows")

    grouped = defaultdict(list)

    for row in rows:

        key = tuple(
            float(row[field])
            for field in parameter_fields
        )

        grouped[key].append(row)

    summaries = []

    excluded_fields = {
        "method",
        "seed",
        "episode_reward",
        "battery_enabled",
        "workload_multiplier",
        *parameter_fields,
    }

    for parameters, group in sorted(grouped.items()):

        seeds = [
            int(row["seed"])
            for row in group
        ]

        if len(seeds) != len(set(seeds)):
            raise ValueError(
                f"Duplicate seeds: {parameters}"
            )

        if set(seeds) != set(cfg.CALIBRATION_SEEDS):
            raise ValueError(
                f"Incomplete seed set: {parameters}"
            )

        summary = dict(
            zip(parameter_fields, parameters)
        )

        summary["runs"] = len(group)

        summary["method"] = group[0]["method"]

        summary["workload_multiplier"] = (
            cfg.WORKLOAD_MULTIPLIER
        )

        summary["battery_enabled"] = True

        for field in group[0]:

            if field in excluded_fields:
                continue

            values = [
                float(row[field])
                for row in group
            ]

            if not all(
                math.isfinite(v)
                for v in values
            ):
                raise ValueError(
                    f"Invalid metric: {field}"
                )

            summary[f"mean_{field}"] = mean(values)

            summary[f"std_{field}"] = pstdev(values)

        summary["min_completion_rate"] = min(
            float(row["completion_rate"])
            for row in group
        )

        summary["feasible"] = (
            summary["mean_completion_rate"]
            >= cfg.MIN_MEAN_COMPLETION_RATE
            and
            summary["min_completion_rate"]
            >= cfg.MIN_SEED_COMPLETION_RATE
        )

        summaries.append(summary)

    return summaries


# ============================================================
# Pareto dominance
# ============================================================

def metric_cost(row, metric):

    direction = cfg.PRIMARY_METRICS[metric]

    value = float(
        row[f"mean_{metric}"]
    )

    # Convert every objective to minimization.
    return -direction * value


def dominates(a, b):

    costs_a = [
        metric_cost(a, metric)
        for metric in cfg.PRIMARY_METRICS
    ]

    costs_b = [
        metric_cost(b, metric)
        for metric in cfg.PRIMARY_METRICS
    ]

    no_worse = all(
        x <= y
        for x, y in zip(costs_a, costs_b)
    )

    strictly_better = any(
        x < y
        for x, y in zip(costs_a, costs_b)
    )

    return no_worse and strictly_better


def get_pareto_front(rows):

    feasible = [
        row for row in rows
        if row["feasible"]
    ]

    return [
        candidate
        for candidate in feasible
        if not any(
            dominates(other, candidate)
            for other in feasible
            if other is not candidate
        )
    ]


# ============================================================
# Average ranks for exact ties
# ============================================================

def assign_average_ranks(rows, metric):

    ordered = sorted(
        rows,
        key=lambda row: metric_cost(
            row, metric
        ),
    )

    i = 0

    while i < len(ordered):

        j = i + 1

        value = metric_cost(
            ordered[i], metric
        )

        while (
            j < len(ordered)
            and metric_cost(
                ordered[j], metric
            ) == value
        ):
            j += 1

        average_rank = (
            (i + 1) + j
        ) / 2.0

        for index in range(i, j):

            ordered[index][
                f"rank_{metric}"
            ] = average_rank

        i = j


# ============================================================
# Rank-sum selection
# ============================================================

def select_parameters(
    summaries,
    parameter_fields,
):

    feasible = [
        dict(row)
        for row in summaries
        if row["feasible"]
    ]

    if not feasible:

        raise RuntimeError(
            "No candidate satisfies completion thresholds."
        )

    pareto = get_pareto_front(feasible)

    pareto_keys = {
        tuple(row[field] for field in parameter_fields)
        for row in pareto
    }

    # Rank against all feasible candidates,
    # not just the Pareto front.
    for metric in cfg.PRIMARY_METRICS:

        assign_average_ranks(
            feasible,
            metric,
        )

    for row in feasible:

        key = tuple(
            row[field]
            for field in parameter_fields
        )

        row["pareto_optimal"] = (
            key in pareto_keys
        )

        row["rank_sum"] = sum(
            row[f"rank_{metric}"]
            for metric in cfg.PRIMARY_METRICS
        )

    def selection_key(row):

        return (
            row["rank_sum"],

            *(
                metric_cost(row, metric)
                for metric in cfg.TIE_BREAK_METRICS
            ),

            *(
                row[field]
                for field in parameter_fields
            ),
        )

    ranking = sorted(
        feasible,
        key=selection_key,
    )

    pareto_ranking = [
        row
        for row in ranking
        if row["pareto_optimal"]
    ]

    selected = pareto_ranking[0]

    for row in ranking:

        row["selected"] = (
            row is selected
        )

    return {
        "ranking": ranking,
        "pareto": pareto_ranking,
        "selected": selected,
    }
