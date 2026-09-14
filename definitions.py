from dagster import Definitions

from finetuning_sequential import (
    finetuning_sequential_job,
    lora_predictor_remote_job,
    saved_assets_exist_check,
    saved_assets_supported_type_check,
)


defs = Definitions(
    jobs=[finetuning_sequential_job, lora_predictor_remote_job],
    asset_checks=[saved_assets_exist_check, saved_assets_supported_type_check],
)
