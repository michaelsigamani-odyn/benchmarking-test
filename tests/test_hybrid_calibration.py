from vidur.training.calibrate_hybrid import HybridCase, fit_weight


def test_fit_weight_prefers_analytical_when_exact() -> None:
    cases = [
        HybridCase(100.0, 100.0, 130.0),
        HybridCase(80.0, 80.0, 120.0),
    ]
    calibration = fit_weight(cases, grid_step=0.1)
    assert calibration.best_weight == 1.0
    assert calibration.best_mape_percent == 0.0


def test_fit_weight_prefers_neusight_when_exact() -> None:
    cases = [
        HybridCase(90.0, 120.0, 90.0),
        HybridCase(70.0, 95.0, 70.0),
    ]
    calibration = fit_weight(cases, grid_step=0.1)
    assert calibration.best_weight == 0.0
    assert calibration.best_mape_percent == 0.0
