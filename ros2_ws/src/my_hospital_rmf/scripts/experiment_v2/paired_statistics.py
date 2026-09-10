#!/usr/bin/env python3

from dataclasses import (
    dataclass,
)

from scipy.stats import (
    wilcoxon,
)


# ==========================================================
# Paired Comparison Result
# ==========================================================

@dataclass(frozen=True)
class PairedComparison:

    metric: str

    method_a: str

    method_b: str

    mean_difference: float

    median_difference: float

    wins_a: int

    wins_b: int

    ties: int

    sample_count: int

    p_value: float | None


# ==========================================================
# Median
# ==========================================================

def calculate_median(
    values: list[float],
) -> float:

    ordered = sorted(
        values
    )

    count = len(
        ordered
    )

    if count == 0:

        raise ValueError(
            "values cannot be empty"
        )

    middle = count // 2

    if count % 2 == 1:

        return ordered[
            middle
        ]

    return (
        ordered[
            middle - 1
        ]
        +
        ordered[
            middle
        ]
    ) / 2.0


# ==========================================================
# Paired Comparison
# ==========================================================

def compare_paired_metric(
    rows: list[dict],
    metric: str,
    method_a: str,
    method_b: str,
    lower_is_better: bool,
) -> PairedComparison:
    """
    使用相同 seed 的結果做 paired comparison。

    Difference 定義：

        method_a - method_b

    因此：

    lower_is_better=True：
        difference < 0
        表示 method_a 比 method_b 好。

    lower_is_better=False：
        difference > 0
        表示 method_a 比 method_b 好。
    """

    values_by_seed = {}

    for row in rows:

        value = row.get(
            metric
        )

        if value is None:

            continue

        seed = row[
            "seed"
        ]

        method = row[
            "method"
        ]

        values_by_seed.setdefault(
            seed,
            {},
        )[
            method
        ] = float(
            value
        )

    paired_values = []

    for seed in sorted(
        values_by_seed
    ):

        methods = (
            values_by_seed[
                seed
            ]
        )

        if (
            method_a
            not in methods
            or
            method_b
            not in methods
        ):

            continue

        paired_values.append(
            (
                methods[
                    method_a
                ],
                methods[
                    method_b
                ],
            )
        )

    if not paired_values:

        raise ValueError(
            "No paired samples found"
        )

    differences = [
        value_a - value_b
        for value_a, value_b
        in paired_values
    ]

    wins_a = 0
    wins_b = 0
    ties = 0

    for difference in differences:

        if abs(
            difference
        ) <= 1e-12:

            ties += 1

        elif lower_is_better:

            if difference < 0.0:

                wins_a += 1

            else:

                wins_b += 1

        else:

            if difference > 0.0:

                wins_a += 1

            else:

                wins_b += 1

    mean_difference = (
        sum(
            differences
        )
        /
        len(
            differences
        )
    )

    median_difference = (
        calculate_median(
            differences
        )
    )

    # ------------------------------------------------------
    # Wilcoxon Signed-Rank Test
    #
    # 如果每一組差異全部都是 0，
    # 沒有可做的統計檢定。
    #
    # 例如目前 Success Rate
    # 很可能就是這種情況。
    # ------------------------------------------------------

    nonzero_differences = [
        difference
        for difference
        in differences
        if abs(difference) > 1e-12
    ]

    # Wilcoxon 需要足夠的非零 paired differences
    # 才有值得解讀的統計意義。
    #
    # 大量 ties（例如 Success Rate 29/30 相同）
    # 只保留 Wins / Ties 描述，不強行輸出 p-value。
    if len(nonzero_differences) < 5:

        p_value = None

    else:

        has_zero_difference = any(
            abs(difference) <= 1e-12
            for difference
            in differences
        )

        statistic = (
            wilcoxon(
                [
                    value_a
                    for value_a, _
                    in paired_values
                ],
                [
                    value_b
                    for _, value_b
                    in paired_values
                ],
                alternative="two-sided",
                zero_method="wilcox",
                method=(
                    "approx"
                    if has_zero_difference
                    else "auto"
                ),
            )
        )

        p_value = float(
            statistic.pvalue
        )

    return PairedComparison(
        metric=metric,
        method_a=method_a,
        method_b=method_b,
        mean_difference=(
            mean_difference
        ),
        median_difference=(
            median_difference
        ),
        wins_a=wins_a,
        wins_b=wins_b,
        ties=ties,
        sample_count=len(
            paired_values
        ),
        p_value=p_value,
    )