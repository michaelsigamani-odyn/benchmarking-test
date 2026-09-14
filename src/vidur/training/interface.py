from abc import ABC, abstractmethod

from .types import StepPrediction, StepRequest


class LoraStepModel(ABC):
    @abstractmethod
    def predict_step(self, request: StepRequest, dataset_tokens: int) -> StepPrediction:
        raise NotImplementedError
