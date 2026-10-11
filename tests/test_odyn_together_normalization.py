from cross_oem_migration.reporting.odyn_together_normalization import (
    compute_finetune_steady_cost_per_million,
    compute_serving_cost_per_million,
    round3,
    validate_regression_counts,
)


def test_serving_reference_values():
    assert round3(compute_serving_cost_per_million(1533, 5.49)) == 0.995

    # Workbook reference checks supplied in the story.
    a100_rate = 10_000 / 8 / 730
    h100_rate = 1_400 / 730
    assert round3(compute_serving_cost_per_million(1505.705, a100_rate)) == 0.316
    assert round3(compute_serving_cost_per_million(1702.322, h100_rate)) == 0.313


def test_finetune_steady_reference_values():
    a100_rate = 10_000 / 8 / 730
    h100_rate = 1_400 / 730
    assert round3(compute_finetune_steady_cost_per_million(a100_rate, 4_447.293)) == 0.107
    assert round3(compute_finetune_steady_cost_per_million(h100_rate, 873.421)) == 0.610


def test_effective_min_charge_pattern_and_list_rate_differs():
    tokens = [287_860, 1_435_064, 2_854_762, 1_672_237]
    effective = [round3(4.0 / (t / 1_000_000.0)) for t in tokens]
    list_rate = [0.34, 0.34, 0.34, 0.40]
    assert all(e is not None for e in effective)
    assert all(abs(e - l) > 1e-6 for e, l in zip(effective, list_rate))


def test_regression_token_count_mismatch_is_detected():
    rows = [
        {"model": "Qwen/Qwen3.5-4B", "tokens": 287_860},
        {"model": "Qwen/Qwen3.5-9B", "tokens": 1_435_064},
        {"model": "Qwen/Qwen3.5-27B", "tokens": 2_854_762},
        {"model": "openai/gpt-oss-20b", "tokens": 1_672_237},
    ]
    assert validate_regression_counts(rows) == []

    bad_rows = rows[:-1] + [{"model": "openai/gpt-oss-20b", "tokens": 1_700_000}]
    errors = validate_regression_counts(bad_rows)
    assert errors
    assert any("gpt-oss-20b" in e for e in errors)
