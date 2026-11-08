"""Pure statistical functions used by the analysis (no I/O, no global state)."""
import math
from collections.abc import Callable, Sequence

import numpy as np
import scipy.stats as st


def logit(p: float, eps: float = 1e-9) -> float:
    """Compute the log-odds of a probability with boundary clipping."""
    p_clipped = min(max(p, eps), 1.0 - eps)
    return float(math.log(p_clipped / (1.0 - p_clipped)))


def wilson_interval(
    successes: int, n: int, z: float = 1.959963984540054
) -> tuple[float, float]:
    """Compute the Wilson score confidence interval for a binomial proportion."""
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    if successes < 0 or successes > n:
        raise ValueError(
            f"successes must be in [0, {n}], got {successes}"
        )
    p = successes / n
    q = 1.0 - p
    denom = 2.0 * (n + z**2)
    center = (2.0 * n * p + z**2) / denom
    delta = (z / denom) * math.sqrt(4.0 * n * p * q + z**2)
    low = 0.0 if successes == 0 else center - delta
    high = 1.0 if successes == n else center + delta
    return float(low), float(high)


def exact_mcnemar_p(b: int, c: int) -> float:
    """Compute the two-sided exact p-value for McNemar test."""
    if b < 0 or c < 0:
        raise ValueError(f"Counts must be non-negative, got b={b}, c={c}")
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = float(st.binomtest(k, n, p=0.5, alternative="two-sided").pvalue)
    return min(1.0, p)


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Compute Holm-Bonferroni adjusted p-values."""
    m = len(p_values)
    if m == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted_indexed: list[tuple[int, float]] = []
    running_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        multiplier = m - rank
        candidate = p * multiplier
        val = min(1.0, max(running_max, candidate, p))
        running_max = val
        adjusted_indexed.append((orig_idx, val))
    result = [0.0] * m
    for orig_idx, val in adjusted_indexed:
        result[orig_idx] = float(val)
    return result


def _check_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")


def bootstrap_ci(
    values: Sequence[float],
    stat: Callable[[np.ndarray], float] = np.mean,
    n_resamples: int = 5000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    """Compute a percentile bootstrap confidence interval."""
    arr = np.asarray(values, dtype=float)
    n = len(arr)
    if n == 0:
        raise ValueError("values must not be empty")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(n_resamples, n))
    resamples = arr[indices]
    _check_alpha(alpha)
    if stat is np.mean:
        estimates = np.mean(resamples, axis=1)
    else:
        estimates = np.fromiter(
            (float(stat(row)) for row in resamples),
            dtype=float,
            count=n_resamples,
        )
    low_pct = 100.0 * (alpha / 2.0)
    high_pct = 100.0 * (1.0 - alpha / 2.0)
    lower = float(np.percentile(estimates, low_pct))
    upper = float(np.percentile(estimates, high_pct))
    return lower, upper


def paired_bootstrap_diff_ci(
    a: Sequence[float],
    b: Sequence[float],
    n_resamples: int = 5000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Compute a paired bootstrap confidence interval for mean(a - b)."""
    _check_alpha(alpha)
    arr_a = np.asarray(a, dtype=float)
    arr_b = np.asarray(b, dtype=float)
    if len(arr_a) != len(arr_b):
        raise ValueError(
            f"Length mismatch: len(a)={len(arr_a)} != len(b)={len(arr_b)}"
        )
    n = len(arr_a)
    if n == 0:
        raise ValueError("Sequences must not be empty")
    diff = arr_a - arr_b
    mean_diff = float(np.mean(diff))
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(n_resamples, n))
    resampled_diffs = diff[indices]
    resampled_means = np.mean(resampled_diffs, axis=1)
    low_pct = 100.0 * (alpha / 2.0)
    high_pct = 100.0 * (1.0 - alpha / 2.0)
    lower = float(np.percentile(resampled_means, low_pct))
    upper = float(np.percentile(resampled_means, high_pct))
    return mean_diff, lower, upper


def auroc(
    positive_scores: Sequence[float], negative_scores: Sequence[float]
) -> float:
    """Compute the Area Under the Receiver Operating Characteristic curve."""
    if len(positive_scores) == 0 or len(negative_scores) == 0:
        raise ValueError(
            "positive_scores and negative_scores must both be non-empty"
        )
    pos = np.asarray(positive_scores, dtype=float)
    neg = np.asarray(negative_scores, dtype=float)
    u_stat = float(
        st.mannwhitneyu(pos, neg, alternative="two-sided").statistic
    )
    return u_stat / (len(pos) * len(neg))


def threshold_at_fpr(negative_scores: Sequence[float], fpr: float) -> float:
    """Find the smallest threshold achieving false positive rate at most fpr."""
    if not 0.0 <= fpr <= 1.0:
        raise ValueError(f"fpr must be in [0, 1], got {fpr}")
    arr = np.asarray(negative_scores, dtype=float)
    n = len(arr)
    if n == 0:
        raise ValueError("negative_scores must not be empty")
    sorted_arr = np.sort(arr)
    unique_vals = np.unique(sorted_arr)
    counts = n - np.searchsorted(sorted_arr, unique_vals, side="left")
    valid = unique_vals[counts / n <= fpr]
    if len(valid) > 0:
        return float(valid[0])
    return float("inf")


def tpr_at_threshold(positive_scores: Sequence[float], threshold: float) -> float:
    """Compute true positive rate at a given decision threshold."""
    arr = np.asarray(positive_scores, dtype=float)
    n = len(arr)
    if n == 0:
        raise ValueError("positive_scores must not be empty")
    return float(np.mean(arr >= threshold))


def tpr_at_fpr(
    positive_scores: Sequence[float], negative_scores: Sequence[float], fpr: float
) -> float:
    """Compute true positive rate at the threshold achieving the given fpr."""
    t = threshold_at_fpr(negative_scores, fpr)
    return tpr_at_threshold(positive_scores, t)


def harrell_davis_quantile(values: Sequence[float], q: float) -> float:
    """Compute the Harrell-Davis quantile estimator using beta weights."""
    arr = np.sort(np.asarray(values, dtype=float))
    n = len(arr)
    if n == 0:
        raise ValueError("values must not be empty")
    if not (0.0 < q < 1.0):
        raise ValueError(f"q must be in (0, 1), got {q}")
    v = np.arange(n + 1) / float(n)
    w_cdf = st.beta.cdf(v, (n + 1) * q, (n + 1) * (1.0 - q))
    weights = w_cdf[1:] - w_cdf[:-1]
    return float(np.dot(weights, arr))


def smoothed_threshold_at_fpr(
    negative_scores: Sequence[float], fpr: float
) -> float:
    """Estimate a decision threshold using the Harrell-Davis quantile estimator."""
    return harrell_davis_quantile(negative_scores, 1.0 - fpr)


def cusum_episode_score(logits: Sequence[float], tau0: float) -> float:
    """Compute CUSUM score as sum over max(0, logit - tau0)."""
    return float(sum(max(0.0, float(value) - tau0) for value in logits))
