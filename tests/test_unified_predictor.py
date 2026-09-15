from pathlib import Path

import pytest

from vidur.training.types import LoraAdapterConfig, ModelConfig, OpPredictor, PredictorBundle, StepRequest
from vidur.training.unified_predictor import NeusightSettings, UnifiedLoraPredictor


def test_hybrid_backend_blends_analytical_and_neusight() -> None:
    predictor = UnifiedLoraPredictor(bundle(), "hybrid", 0.25, neusight_settings(), neusight_runner=lambda _settings, _request: 40.0)
    unified = predictor.predict_step(request(), dataset_tokens=2048)
    expected = (0.25 * unified.analytical_step_ms) + (0.75 * 40.0)
    assert unified.prediction.step_time.total_ms() == pytest.approx(expected)


def test_neusight_backend_requires_neusight_settings() -> None:
    predictor = UnifiedLoraPredictor(bundle(), "neusight", 0.5, None)
    with pytest.raises(ValueError, match="NeuSight prediction requested"):
        predictor.predict_step(request(), dataset_tokens=2048)


def bundle() -> PredictorBundle:
    predictors = {
        "attention:forward:bf16": OpPredictor("attention", "forward", 1.0, 0.0),
        "attention:backward:bf16": OpPredictor("attention", "backward", 2.0, 0.0),
        "base_linear:forward:bf16": OpPredictor("base_linear", "forward", 3.0, 0.0),
        "base_linear:backward:bf16": OpPredictor("base_linear", "backward", 4.0, 0.0),
        "adamw:step:bf16": OpPredictor("adamw", "step", 5.0, 0.0),
    }
    return PredictorBundle(predictors, {"dgx_spark_gb10": 7.0}, {"checkpoint_off": 1.0, "checkpoint_on": 1.0})


def request() -> StepRequest:
    model = ModelConfig("tinyllama", 1024, 4096, 2, 16, 32000, 1_100_000_000)
    lora = LoraAdapterConfig(16, 32, ("q_proj", "v_proj"), 0.05)
    return StepRequest(model, 2, 512, lora, False, "bf16", "dgx_spark_gb10")


def neusight_settings() -> NeusightSettings:
    return NeusightSettings("neusight", Path("."), Path("."), Path("."), "", "", None)
