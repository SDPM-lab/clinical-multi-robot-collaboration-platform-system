from pathlib import Path
from itertools import product
from collections import Counter
import hashlib
import json
import csv
import io

import numpy as np
import pandas as pd

from scipy.stats import (
    rankdata,
    ttest_rel,
    wilcoxon,
)

DOC = Path(__file__).resolve().parent
DATA = DOC / "data"

S1 = DATA / "stage1_initial_sweep"
S2 = DATA / "stage2_pareto_confirmation"
S3 = DATA / "stage3_nav2_confirmation"
S4 = DATA / "stage4_final_selection"

METRICS = [
    "average_waiting_time_s",
    "p95_waiting_time_s",
    "high_waiting_time_s",
    "emergency_waiting_time_s",
    "total_travel_time_s",
    "jain_task_fairness",
]

SHORT = [
    "avg_wait",
    "p95_wait",
    "high_wait",
    "emergency_wait",
    "total_travel",
    "jain_fairness",
]

WEIGHTS = [
    "waiting_weight",
    "approach_weight",
    "queue_weight",
    "imbalance_weight",
]

STAGE2_CONFIGS = [
    3, 4, 6, 9, 10,
    12, 13, 17, 19, 21,
    23, 25, 27, 30, 33
]

STAGE3_CONFIGS = [
    3, 4, 6, 12, 21, 25, 27
]

MODEL_SEEDS = [
    7001, 7101, 7102, 7103, 7104
]

EVAL_SEEDS = list(range(9501, 9531))

BOOTSTRAPS = 10000
RNG_SEED = 20261127

generated = {}
pending = {}


def sha256(path):

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def save(df, path):

    content = df.to_csv(
        index=False,
        lineterminator="\n",
        float_format="%.12g",
    ).encode("utf-8")

    if path.exists() and path.read_bytes() != content:

        raise RuntimeError(
            f"Existing analysis differs: {path}"
        )

    pending[path] = content

    generated[str(path.relative_to(DOC))] = {
        "rows": len(df),
        "sha256": hashlib.sha256(content).hexdigest(),
    }

    print(
        "Prepared:",
        path.relative_to(DOC),
        f"({len(df)} rows)"
    )


def sweep_name(n):

    return f"sweep{int(n):02d}"


def sweep_names(numbers):

    return [sweep_name(n) for n in numbers]


# ============================================================
# 1. Verify archived source files
# ============================================================

manifest_path = DATA / "reward_selection_manifest.json"

archive_manifest = json.loads(
    manifest_path.read_text()
)

assert len(archive_manifest["files"]) == 161

for entry in archive_manifest["files"]:

    path = DOC / entry["archive"]

    assert path.is_file(), path

    assert sha256(path) == entry["sha256"], (
        f"Archive hash mismatch: {path}"
    )

print("===== SOURCE ARCHIVE VERIFIED =====")
print("Archived files: 161")
print("SHA256: PASS")


# ============================================================
# 2. Pareto and rank analysis
# ============================================================

def pareto_analysis(df):

    df = df.copy()

    assert df["config"].is_unique

    names = df["config"].tolist()

    columns = [
        f"{m}_mean" for m in METRICS
    ]

    values = df[columns].to_numpy(dtype=float)

    assert np.isfinite(values).all()

    objective_values = values.copy()

    # Jain fairness: higher is better.
    objective_values[:, -1] *= -1

    ranks = np.column_stack([
        rankdata(
            objective_values[:, j],
            method="average"
        )
        for j in range(len(METRICS))
    ])

    for j, name in enumerate(SHORT):

        df[f"rank_{name}"] = ranks[:, j]

    df["rank_sum"] = ranks.sum(axis=1)

    df["overall_rank"] = rankdata(
        df["rank_sum"],
        method="min"
    ).astype(int)

    dominated_by = []

    for i in range(len(names)):

        dominators = []

        for j in range(len(names)):

            if i == j:
                continue

            x = objective_values[j]
            y = objective_values[i]

            if np.all(x <= y) and np.any(x < y):

                dominators.append(names[j])

        dominated_by.append(dominators)

    df["is_pareto"] = [
        not x for x in dominated_by
    ]

    df["dominator_count"] = [
        len(x) for x in dominated_by
    ]

    df["dominated_by"] = [
        ";".join(sorted(x))
        for x in dominated_by
    ]

    return df.sort_values("config").reset_index(drop=True)


def show_stage(title, df):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)

    print(
        df[
            [
                "config",
                "rank_sum",
                "overall_rank",
                "is_pareto",
                "dominated_by",
            ]
        ].sort_values(
            ["rank_sum", "config"]
        ).to_string(index=False)
    )

    print()
    print(
        "Pareto:",
        df.loc[
            df["is_pareto"],
            "config"
        ].tolist()
    )


# ============================================================
# Stage 1: 33 -> 15
# ============================================================

stage1 = pd.read_csv(
    S1 / "reward_sweep_validation_summary.csv"
)

assert len(stage1) == 33

stage1["config"] = stage1[
    "sweep_index"
].map(sweep_name)

assert set(stage1["config"]) == set(
    sweep_names(range(1, 34))
)

stage1 = pareto_analysis(stage1)

pareto1 = sorted(
    stage1.loc[
        stage1["is_pareto"],
        "config"
    ]
)

assert pareto1 == sweep_names(
    STAGE2_CONFIGS
)

stage1["selected_for_next_stage"] = (
    stage1["is_pareto"]
)

save(
    stage1,
    S1 / "pareto_analysis.csv"
)

show_stage(
    "STAGE 1: 33 -> 15",
    stage1
)


# ============================================================
# Stage 2: 15 -> 7
# ============================================================

stage2 = pd.read_csv(
    S2 / "confirmation_config_summary.csv"
)

assert len(stage2) == 15

assert set(stage2["config"]) == set(
    pareto1
)

stage2 = pareto_analysis(stage2)

pareto2 = sorted(
    stage2.loc[
        stage2["is_pareto"],
        "config"
    ]
)

assert pareto2 == sweep_names(
    STAGE3_CONFIGS
)

stage2["selected_for_next_stage"] = (
    stage2["is_pareto"]
)

save(
    stage2,
    S2 / "pareto_analysis.csv"
)

show_stage(
    "STAGE 2: 15 -> 7",
    stage2
)


# ============================================================
# Stage 3: 7 -> 2
# ============================================================

stage3 = pd.read_csv(
    S3 / "confirmation_config_summary.csv"
)

assert len(stage3) == 7

assert set(stage3["config"]) == set(
    pareto2
)

stage3 = pareto_analysis(stage3)

pareto3 = sorted(
    stage3.loc[
        stage3["is_pareto"],
        "config"
    ]
)

assert len(pareto3) == 6

final_candidates = (
    stage3.loc[stage3["is_pareto"]]
    .sort_values(["rank_sum", "config"])
    .head(2)["config"]
    .tolist()
)

assert final_candidates == [
    "sweep25",
    "sweep12"
]

stage3["selected_for_next_stage"] = (
    stage3["config"].isin(
        final_candidates
    )
)

save(
    stage3,
    S3 / "pareto_analysis.csv"
)

show_stage(
    "STAGE 3: 7 -> 2",
    stage3
)

print(
    "Final candidates:",
    final_candidates
)


# ============================================================
# 3. All 35 Nav2 model rankings
# ============================================================

models = pd.read_csv(
    S3 / "confirmation_model_summary.csv"
)

expected_models = set(product(
    sweep_names(STAGE3_CONFIGS),
    MODEL_SEEDS,
))

actual_models = set(zip(
    models["config"],
    models["model_seed"]
))

assert len(models) == 35
assert actual_models == expected_models

assert not models.duplicated(
    ["config", "model_seed"]
).any()


def add_model_ranks(df, prefix):

    df = df.copy()

    values = df[METRICS].to_numpy(
        dtype=float,
        copy=True
    )

    values[:, -1] *= -1

    ranks = np.column_stack([
        rankdata(
            values[:, j],
            method="average"
        )
        for j in range(len(METRICS))
    ])

    for j, name in enumerate(SHORT):

        df[f"{prefix}_rank_{name}"] = ranks[:, j]

    df[f"{prefix}_rank_sum"] = ranks.sum(axis=1)

    df[f"{prefix}_rank"] = rankdata(
        ranks.sum(axis=1),
        method="min"
    ).astype(int)

    return df


models = add_model_ranks(
    models,
    "global"
)

models = pd.concat(
    [
        add_model_ranks(group, "within_config")
        for _, group in models.groupby("config")
    ],
    ignore_index=True
)

models = models.sort_values(
    ["global_rank_sum", "config", "model_seed"]
)

save(
    models,
    S3 / "model_ranking.csv"
)

print()
print("===== TOP 5 NAV2 MODELS =====")

print(
    models[
        [
            "config",
            "model_seed",
            "global_rank_sum",
            "global_rank",
        ]
    ].head(5).to_string(index=False)
)


# ============================================================
# 4. Final candidates: paired statistical analysis
# ============================================================

episodes = pd.read_csv(
    S3 / "confirmation_episode_runs.csv"
)

expected_episodes = set(product(
    sweep_names(STAGE3_CONFIGS),
    MODEL_SEEDS,
    EVAL_SEEDS
))

actual_episodes = set(zip(
    episodes["config"],
    episodes["model_seed"],
    episodes["seed"],
))

assert len(episodes) == 1050
assert actual_episodes == expected_episodes

assert not episodes.duplicated(
    ["config", "model_seed", "seed"]
).any()

assert (episodes["completion_rate"] == 1).all()

episodes = episodes.set_index(
    ["config", "model_seed", "seed"]
)


def matrix(config, metric):

    return np.array([
        [
            episodes.loc[
                (config, ms, es),
                metric
            ]
            for es in EVAL_SEEDS
        ]
        for ms in MODEL_SEEDS
    ], dtype=float)


def holm_adjust(p_values):

    p_values = np.asarray(
        p_values,
        dtype=float
    )

    order = np.argsort(p_values)

    adjusted = np.empty(len(p_values))

    running = 0.0

    for position, idx in enumerate(order):

        running = max(
            running,
            (len(p_values) - position)
            * p_values[idx]
        )

        adjusted[idx] = min(1.0, running)

    return adjusted


rng = np.random.default_rng(
    RNG_SEED
)

model_idx = rng.integers(
    0,
    len(MODEL_SEEDS),
    size=(BOOTSTRAPS, len(MODEL_SEEDS))
)

eval_idx = rng.integers(
    0,
    len(EVAL_SEEDS),
    size=(BOOTSTRAPS, len(EVAL_SEEDS))
)

historical = pd.read_csv(
    S4 / "hierarchical_paired_bootstrap.csv"
).set_index("metric")

assert set(historical.index) == set(METRICS)

statistics = []

for metric in METRICS:

    a = matrix("sweep12", metric)
    b = matrix("sweep25", metric)

    # Positive difference always means Sweep12 better.
    if metric == "jain_task_fairness":

        diff = a - b
        direction = "higher"

    else:

        diff = b - a
        direction = "lower"

    d = diff.mean(axis=1)

    sampled = diff[
        model_idx[:, :, None],
        eval_idx[:, None, :]
    ]

    boot = sampled.mean(
        axis=(1, 2)
    )

    low, high = np.percentile(
        boot,
        [2.5, 97.5]
    )

    observed = float(diff.mean())

    hist = historical.loc[metric]

    assert np.isclose(
        observed,
        -float(hist["observed_difference"])
    )

    t_p = (
        1.0 if np.all(d == 0)
        else float(
            ttest_rel(
                a.mean(axis=1),
                b.mean(axis=1)
            ).pvalue
        )
    )

    w_p = (
        1.0 if np.all(d == 0)
        else float(wilcoxon(d).pvalue)
    )

    statistics.append({
        "metric": metric,
        "direction": direction,
        "positive_difference_means": "sweep12_better",
        "model_seed_count": len(MODEL_SEEDS),
        "evaluation_seed_count": len(EVAL_SEEDS),

        "sweep12_mean": float(a.mean()),
        "sweep12_sd": float(
            a.mean(axis=1).std(ddof=1)
        ),

        "sweep25_mean": float(b.mean()),
        "sweep25_sd": float(
            b.mean(axis=1).std(ddof=1)
        ),

        "observed_difference": observed,

        "relative_improvement_pct": (
            100 * observed / float(b.mean())
        ),

        # Original historical bootstrap.
        # Convert its direction to Sweep12 better.
        "historical_ci95_low": (
            -float(hist["ci95_high"])
        ),

        "historical_ci95_high": (
            -float(hist["ci95_low"])
        ),

        "historical_conclusion_original": (
            hist["conclusion"]
        ),

        # New crossed bootstrap.
        "crossed_ci95_low": float(low),
        "crossed_ci95_high": float(high),

        "crossed_conclusion": (
            "sweep12_better" if low > 0
            else "sweep25_better" if high < 0
            else "ci_crosses_zero"
        ),

        "paired_t_p": t_p,
        "wilcoxon_p": w_p,

        "sweep12_wins": int((d > 0).sum()),
        "sweep25_wins": int((d < 0).sum()),
        "ties": int((d == 0).sum()),
    })

stats = pd.DataFrame(statistics)

stats["holm_t_p"] = holm_adjust(
    stats["paired_t_p"]
)

stats["holm_wilcoxon_p"] = holm_adjust(
    stats["wilcoxon_p"]
)

save(
    stats,
    S4 / "final_candidate_statistics.csv"
)

print()
print("===== FINAL CANDIDATE STATISTICS =====")

print(
    stats[
        [
            "metric",
            "observed_difference",
            "crossed_ci95_low",
            "crossed_ci95_high",
            "sweep12_wins",
            "holm_t_p",
        ]
    ].to_string(index=False)
)


# ============================================================
# 5. Emergency wait by paired model seed
# ============================================================

metric = "emergency_waiting_time_s"

a = matrix(
    "sweep12", metric
).mean(axis=1)

b = matrix(
    "sweep25", metric
).mean(axis=1)

emergency = pd.DataFrame({
    "model_seed": MODEL_SEEDS,

    "sweep12_emergency_wait_s": a,

    "sweep25_emergency_wait_s": b,

    "improvement_s": b - a,

    "improvement_pct": (
        100 * (b - a) / b
    ),

    "winner": np.where(
        a < b,
        "sweep12",
        np.where(
            a > b,
            "sweep25",
            "tie"
        )
    )
})

assert (
    emergency["winner"] == "sweep12"
).all()

save(
    emergency,
    S4 / "emergency_wait_by_seed.csv"
)

print()
print("===== EMERGENCY WAIT BY SEED =====")

print(
    emergency.to_string(index=False)
)


# ============================================================
# 6. Representative model selection
# ============================================================

representative = models.loc[
    models["config"] == "sweep12"
].copy()

representative = representative.sort_values(
    "model_seed"
)

values = representative[
    METRICS
].to_numpy(dtype=float)

config_mean = values.mean(axis=0)

config_sd = values.std(
    axis=0, ddof=1
)

z = (
    values - config_mean
) / np.where(
    config_sd == 0,
    1.0,
    config_sd
)

for j, short in enumerate(SHORT):

    representative[
        f"config_mean_{short}"
    ] = config_mean[j]

    representative[
        f"config_sd_{short}"
    ] = config_sd[j]

    representative[
        f"standardized_difference_{short}"
    ] = z[:, j]

representative[
    "standardized_distance_to_mean"
] = np.sqrt(
    np.mean(z ** 2, axis=1)
)

representative["representativeness_rank"] = (
    rankdata(
        representative[
            "standardized_distance_to_mean"
        ],
        method="min"
    ).astype(int)
)

representative["is_best_performance"] = (
    representative["within_config_rank"] == 1
)

representative["is_closest_to_mean"] = (
    representative["representativeness_rank"] == 1
)

representative["used_in_final_baseline_evaluation"] = (
    representative["model_seed"] == 7101
)

best_seed = int(
    representative.loc[
        representative["is_best_performance"],
        "model_seed"
    ].iloc[0]
)

typical_seed = int(
    representative.loc[
        representative["is_closest_to_mean"],
        "model_seed"
    ].iloc[0]
)

assert best_seed == 7104
assert typical_seed == 7101

representative = representative.sort_values(
    "representativeness_rank"
)

save(
    representative,
    S4 / "representative_model_selection.csv"
)

print()
print("===== REPRESENTATIVE MODEL SELECTION =====")

print(
    representative[
        [
            "model_seed",
            "within_config_rank_sum",
            "within_config_rank",
            "standardized_distance_to_mean",
            "representativeness_rank",
        ]
    ].to_string(index=False)
)

print()
print("Best performance seed:", best_seed)
print("Closest to mean seed:", typical_seed)


# ============================================================
# 7. Analysis provenance and manifest
# ============================================================

analysis_manifest = {
    "scope": "33 -> 15 -> 7 -> 2 -> 1",

    "analysis_type": (
        "Retrospective analysis of archived experiments"
    ),

    "archive_manifest_sha256": (
        sha256(manifest_path)
    ),

    "analysis_script_sha256": (
        sha256(Path(__file__))
    ),

    "stage1": {
        "environment": "preliminary",
        "configurations": 33,
        "models": 33,
        "episodes": 660,
        "pareto": pareto1,
    },

    "stage2": {
        "environment": "preliminary",
        "configurations": 15,
        "models": 75,
        "episodes": 1500,
        "pareto": pareto2,
    },

    "stage3": {
        "environment": "nav2_calibrated",
        "configurations": 7,
        "models": 35,
        "episodes": 1050,
        "pareto": pareto3,
        "final_candidates": final_candidates,
    },

    "stage4": {
        "selected_config": "sweep12",

        "selection_basis": (
            "Medical emergency-task priority; "
            "descriptive paired improvement, "
            "not robust statistical superiority"
        ),

        "best_performance_seed": best_seed,

        "closest_to_config_mean_seed": typical_seed,

        "formal_baseline_model_seed": 7101,

        "deployment_verified": False,
    },

    "statistics": {
        "objectives": METRICS,

        "rank_sum": "Equal metric ranks",

        "rank_tie_method": "average",

        "bootstrap_repetitions": BOOTSTRAPS,

        "bootstrap_rng_seed": RNG_SEED,

        "bootstrap_type": (
            "Crossed paired model/scenario resampling"
        ),

        "confidence_level": 0.95,

        "holm_correction": (
            "Separate six-metric families "
            "for paired t and Wilcoxon tests"
        ),

        "representative_distance": (
            "Root mean square of standardized "
            "metric deviations"
        ),
    },

    "limitations": [
        "Stage1 and Stage2 use the preliminary environment.",
        "Only seven configurations were retrained under Nav2.",
        "Final candidate comparison has five model seeds.",
        "Crossed bootstrap intervals are pointwise.",
        "Candidate selection is retrospective.",
        "Seed7101 representativeness analysis is retrospective.",
        "Formal evaluation model deployment remains unverified.",
    ],

    "generated_files": generated,
}

manifest_out = (
    DATA / "reward_selection_analysis_manifest.json"
)

manifest_content = (
    json.dumps(
        analysis_manifest,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    ) + "\n"
).encode("utf-8")

if (
    manifest_out.exists()
    and manifest_out.read_bytes() != manifest_content
):

    raise RuntimeError(
        "Existing analysis manifest differs."
    )

# All calculations and assertions have passed.
# Only now write derived analysis files.

for path, content in pending.items():

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if not path.exists():

        path.write_bytes(content)

if not manifest_out.exists():

    manifest_out.write_bytes(
        manifest_content
    )

print()
print("===== GENERATED ANALYSIS FILES =====")

for name, record in generated.items():

    print(
        name,
        "Rows:", record["rows"]
    )

print()
print("===== REWARD SELECTION ANALYSIS COMPLETE =====")

print("Stage 1: 33 -> 15 PASS")
print("Stage 2: 15 -> 7 PASS")
print("Stage 3: 7 -> 2 PASS")
print("Stage 4: Sweep12 selection analysis PASS")
print("Representative Seed7101: PASS")

print("Generated CSV files:", len(generated))
print("Historical source files modified: NO")
print("Archived source files modified: NO")
print("Models retrained: NO")
print("New simulation runs: 0")

