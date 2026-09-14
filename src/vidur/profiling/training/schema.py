from dataclasses import asdict
from typing import Dict, List

from vidur.training.types import OpProfilePoint


def csv_fields() -> List[str]:
    return list(asdict(empty_point()).keys())


def empty_point() -> OpProfilePoint:
    return OpProfilePoint("", "", "", 0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, False, "")


def point_to_row(point: OpProfilePoint) -> Dict[str, str]:
    row = asdict(point)
    row["ok"] = "1" if point.ok else "0"
    return {key: str(value) for key, value in row.items()}
