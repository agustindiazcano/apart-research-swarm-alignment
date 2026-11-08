from collections.abc import Sequence
import math
from pathlib import Path
import sys

import numpy as np
import pytest
import scipy.stats as st
from scipy.stats.mstats import hdquantiles
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swarmlab.metrics.stats import (
    auroc,
    bootstrap_ci,
    cusum_episode_score,
    exact_mcnemar_p,
    harrell_davis_quantile,
    holm_adjust,
    logit,
    paired_bootstrap_diff_ci,
    smoothed_threshold_at_fpr,
    threshold_at_fpr,
    tpr_at_fpr,
    tpr_at_threshold,
    wilson_interval,
)


def test_logit() -> None:
    # Analytic derivation: log(0.5 / (1.0 - 0.5)) = log(1.0) = 0.0
    assert math.isclose(logit(0.5), 0.0, abs_tol=1e-12)

    # Extreme bounds clipped to eps and 1 - eps
    eps = 1e-4
    expected_low = math.log(eps / (1.0 - eps))
    expected_high = math.log((1.0 - eps) / eps)
    assert math.isclose(logit(-1.0, eps=eps), expected_low, rel_tol=1e-9)
    assert math.isclose(logit(2.0, eps=eps), expected_high, rel_tol=1e-9)

    # Monotonicity check
    p_vals = [0.1, 0.3, 0.5, 0.7, 0.9]
    logit_vals = [logit(p) for p in p_vals]
    assert all(x < y for x, y in zip(logit_vals[:-1], logit_vals[1:]))

    # Symmetry check: logit(p) == -logit(1 - p)
    for p in [0.1, 0.25, 0.4, 0.7]:
        assert math.isclose(logit(p), -logit(1.0 - p), rel_tol=1e-9)


def test_wilson_interval() -> None:
    # Compare against scipy.stats.binomtest proportion_ci with wilson method
    test_cases = [(0, 30), (30, 30), (0, 20), (7, 15), (10, 50), (1, 100)]
    for successes, n in test_cases:
        low, high = wilson_interval(successes, n)
        ref = st.binomtest(successes, n).proportion_ci(
            confidence_level=0.95, method="wilson"
        )
        assert np.isclose(low, ref.low, rtol=1e-12, atol=1e-12)
        assert np.isclose(high, ref.high, rtol=1e-12, atol=1e-12)

    # Test ValueError cases
    with pytest.raises(ValueError):
        wilson_interval(-1, 10)
    with pytest.raises(ValueError):
        wilson_interval(11, 10)
    with pytest.raises(ValueError):
        wilson_interval(0, 0)
    with pytest.raises(ValueError):
        wilson_interval(5, -5)


def test_exact_mcnemar_p() -> None:
    # Compare with scipy.stats.binomtest p-value
    cases = [(1, 5), (10, 10), (0, 10), (5, 2), (15, 3), (25, 12)]
    for b, c in cases:
        p_val = exact_mcnemar_p(b, c)
        ref = float(st.binomtest(min(b, c), b + c, p=0.5, alternative="two-sided").pvalue)
        ref_capped = min(1.0, ref)
        assert np.isclose(p_val, ref_capped, rtol=1e-12, atol=1e-12)
        # Symmetry check
        assert np.isclose(p_val, exact_mcnemar_p(c, b), rtol=1e-12, atol=1e-12)

    # Edge case b + c == 0
    assert exact_mcnemar_p(0, 0) == 1.0

    # Negative counts raise ValueError
    with pytest.raises(ValueError):
        exact_mcnemar_p(-1, 5)
    with pytest.raises(ValueError):
        exact_mcnemar_p(5, -1)


def test_holm_adjust_example() -> None:
    # Derivation of Holm-Bonferroni adjustment for raw p-values [0.01, 0.04, 0.03]:
    # 1. Total hypotheses m = 3.
    # 2. Sort raw p-values with original indices:
    #    index 0: 0.01
    #    index 2: 0.03
    #    index 1: 0.04
    # 3. Step 1 (rank 0): multiplier = 3 - 0 = 3; candidate = 3 * 0.01 = 0.03; adj = 0.03.
    # 4. Step 2 (rank 1): multiplier = 3 - 1 = 2; candidate = 2 * 0.03 = 0.06; adj = max(0.03, 0.06) = 0.06.
    # 5. Step 3 (rank 2): multiplier = 3 - 2 = 1; candidate = 1 * 0.04 = 0.04; adj = max(0.06, 0.04) = 0.06.
    # 6. Map back to original indices [0, 1, 2]:
    #    index 0: 0.03
    #    index 1: 0.06
    #    index 2: 0.06
    # Expected result: [0.03, 0.06, 0.06]
    raw = [0.01, 0.04, 0.03]
    expected = [0.03, 0.06, 0.06]
    adjusted = holm_adjust(raw)
    assert np.allclose(adjusted, expected, rtol=1e-12, atol=1e-12)

    # Empty list edge case
    assert holm_adjust([]) == []


def test_holm_adjust_properties() -> None:
    rng = np.random.default_rng(2026)
    raw = rng.uniform(0.0, 0.5, size=25).tolist()
    adj = holm_adjust(raw)

    # 1. Length and original order preserved
    assert len(adj) == len(raw)

    # 2. Each adjusted value is at least its raw value
    assert all(a >= r for a, r in zip(adj, raw))

    # 3. Capped at 1.0
    assert all(a <= 1.0 for a in adj)

    # 4. Monotone non-decreasing in the sorted order of raw p-values
    sorted_pairs = sorted(zip(raw, adj), key=lambda x: x[0])
    sorted_adj = [pair[1] for pair in sorted_pairs]
    assert all(x <= y for x, y in zip(sorted_adj[:-1], sorted_adj[1:]))


def test_auroc() -> None:
    # Random data with ties compared against sklearn.metrics.roc_auc_score
    rng = np.random.default_rng(42)
    pos = rng.integers(0, 10, size=50).astype(float).tolist()
    neg = rng.integers(0, 10, size=60).astype(float).tolist()

    y_true = [1] * len(pos) + [0] * len(neg)
    y_score = pos + neg
    expected = float(roc_auc_score(y_true, y_score))
    calculated = auroc(pos, neg)
    assert np.isclose(calculated, expected, rtol=1e-12, atol=1e-12)

    # Perfect separation case
    pos_perfect = [10.0, 20.0, 30.0]
    neg_perfect = [1.0, 2.0, 3.0]
    assert np.isclose(auroc(pos_perfect, neg_perfect), 1.0, rtol=1e-12, atol=1e-12)

    # Reversed separation case
    pos_reversed = [1.0, 2.0, 3.0]
    neg_reversed = [10.0, 20.0, 30.0]
    assert np.isclose(auroc(pos_reversed, neg_reversed), 0.0, rtol=1e-12, atol=1e-12)

    # ValueError on empty inputs
    with pytest.raises(ValueError):
        auroc([], [1.0, 2.0])
    with pytest.raises(ValueError):
        auroc([1.0, 2.0], [])


def test_threshold_at_fpr_and_tpr() -> None:
    # Hand-built derivation:
    # Negatives: [1.0, 2.0, 3.0, 4.0, 5.0], N = 5.
    # Share of negatives with score >= t:
    # t = 1.0 -> 5/5 = 1.0
    # t = 2.0 -> 4/5 = 0.8
    # t = 3.0 -> 3/5 = 0.6
    # t = 4.0 -> 2/5 = 0.4
    # t = 5.0 -> 1/5 = 0.2
    # Smallest threshold with share <= 0.4 is 4.0
    # Smallest threshold with share <= 0.2 is 5.0
    # For fpr = 0.1, no threshold meets share <= 0.1, returns inf
    negs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert threshold_at_fpr(negs, 0.4) == 4.0
    assert threshold_at_fpr(negs, 0.2) == 5.0
    assert threshold_at_fpr(negs, 0.1) == float("inf")
    assert threshold_at_fpr(negs, 1.0) == 1.0

    # Realized FPR on larger random sample is at most the target FPR
    rng = np.random.default_rng(999)
    sample_negs = rng.normal(loc=0.0, scale=1.0, size=200).tolist()
    for target_fpr in [0.05, 0.10, 0.25, 0.50]:
        t = threshold_at_fpr(sample_negs, target_fpr)
        if t != float("inf"):
            realized = float(np.mean(np.asarray(sample_negs) >= t))
            assert realized <= target_fpr

    # tpr_at_threshold checks
    positives = [2.5, 4.5]
    # Positives >= 4.0 is [4.5], share = 1 / 2 = 0.5
    assert tpr_at_threshold(positives, 4.0) == 0.5
    assert tpr_at_threshold(positives, float("inf")) == 0.0
    assert tpr_at_threshold(positives, float("-inf")) == 1.0

    # tpr_at_fpr consistency check
    assert tpr_at_fpr(positives, negs, 0.4) == 0.5
    assert tpr_at_fpr(positives, negs, 0.1) == 0.0

    # ValueError on empty inputs
    with pytest.raises(ValueError):
        threshold_at_fpr([], 0.1)
    with pytest.raises(ValueError):
        tpr_at_threshold([], 1.0)


def test_harrell_davis_quantile() -> None:
    # Compare with scipy.stats.mstats.hdquantiles
    data = [1.2, 2.5, 3.7, 4.0, 5.1, 6.3, 7.0, 8.2, 9.4]
    quantiles = [0.1, 0.25, 0.5, 0.75, 0.9]
    for q in quantiles:
        calculated = harrell_davis_quantile(data, q)
        ref = float(hdquantiles(data, prob=[q])[0])
        assert np.isclose(calculated, ref, rtol=1e-12, atol=1e-12)

    # Random normal dataset
    rng = np.random.default_rng(123)
    random_data = rng.normal(size=50).tolist()
    for q in [0.05, 0.5, 0.95]:
        calculated = harrell_davis_quantile(random_data, q)
        ref = float(hdquantiles(random_data, prob=[q])[0])
        assert np.isclose(calculated, ref, rtol=1e-12, atol=1e-12)

    # ValueError checks
    with pytest.raises(ValueError):
        harrell_davis_quantile([], 0.5)
    with pytest.raises(ValueError):
        harrell_davis_quantile(data, 0.0)
    with pytest.raises(ValueError):
        harrell_davis_quantile(data, 1.0)
    with pytest.raises(ValueError):
        harrell_davis_quantile(data, -0.1)


def test_smoothed_threshold_at_fpr() -> None:
    data = [1.2, 2.5, 3.7, 4.0, 5.1, 6.3, 7.0, 8.2, 9.4]
    for fpr in [0.1, 0.25, 0.5, 0.75, 0.9]:
        smoothed_t = smoothed_threshold_at_fpr(data, fpr)
        expected = harrell_davis_quantile(data, 1.0 - fpr)
        assert np.isclose(smoothed_t, expected, rtol=1e-12, atol=1e-12)


def test_bootstrap_ci() -> None:
    rng = np.random.default_rng(77)
    sample = rng.normal(loc=10.0, scale=2.0, size=40).tolist()

    # Determinism for equal seeds
    ci1 = bootstrap_ci(sample, seed=42)
    ci2 = bootstrap_ci(sample, seed=42)
    assert ci1 == ci2

    # Different seeds produce different intervals
    ci3 = bootstrap_ci(sample, seed=43)
    assert ci1 != ci3

    # Constant sample has zero width
    constant_sample = [7.5] * 25
    low, high = bootstrap_ci(constant_sample, seed=0)
    assert np.isclose(low, 7.5, rtol=1e-12, atol=1e-12)
    assert np.isclose(high, 7.5, rtol=1e-12, atol=1e-12)
    assert np.isclose(high - low, 0.0, abs_tol=1e-12)

    # Non-default stat
    med_low, med_high = bootstrap_ci(sample, stat=np.median, seed=0)
    assert med_low <= med_high

    # Empty sample raises ValueError
    with pytest.raises(ValueError):
        bootstrap_ci([], seed=0)


def test_paired_bootstrap_diff_ci() -> None:
    rng = np.random.default_rng(88)
    a = rng.normal(loc=5.0, scale=1.0, size=30).tolist()
    b = rng.normal(loc=4.0, scale=1.0, size=30).tolist()

    # Identical lists return (0.0, 0.0, 0.0)
    res_identical = paired_bootstrap_diff_ci(a, a, seed=0)
    assert res_identical == (0.0, 0.0, 0.0)

    # Length mismatch raises ValueError
    with pytest.raises(ValueError):
        paired_bootstrap_diff_ci(a, a[:10], seed=0)
    with pytest.raises(ValueError):
        paired_bootstrap_diff_ci([], [], seed=0)

    # Mean difference matches numpy mean
    mean_diff, low, high = paired_bootstrap_diff_ci(a, b, seed=12)
    expected_mean = float(np.mean(np.asarray(a) - np.asarray(b)))
    assert np.isclose(mean_diff, expected_mean, rtol=1e-12, atol=1e-12)
    assert low <= mean_diff <= high

    # Determinism
    res1 = paired_bootstrap_diff_ci(a, b, seed=12)
    res2 = paired_bootstrap_diff_ci(a, b, seed=12)
    assert res1 == res2


def test_cusum_episode_score() -> None:
    # Hand-built derivation for logits = [-1.0, 0.5, 2.0, 1.5] and tau0 = 1.0:
    # Term 1: max(0.0, -1.0 - 1.0) = max(0.0, -2.0) = 0.0
    # Term 2: max(0.0, 0.5 - 1.0)  = max(0.0, -0.5) = 0.0
    # Term 3: max(0.0, 2.0 - 1.0)  = max(0.0, 1.0)  = 1.0
    # Term 4: max(0.0, 1.5 - 1.0)  = max(0.0, 0.5)  = 0.5
    # Total sum = 0.0 + 0.0 + 1.0 + 0.5 = 1.5
    logits = [-1.0, 0.5, 2.0, 1.5]
    assert cusum_episode_score(logits, tau0=1.0) == 1.5

    # Empty logits returns 0.0
    assert cusum_episode_score([], tau0=1.0) == 0.0

    # All logits below tau0
    assert cusum_episode_score([-2.0, -1.0, 0.0], tau0=0.5) == 0.0
