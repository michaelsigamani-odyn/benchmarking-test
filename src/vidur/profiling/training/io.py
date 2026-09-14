import csv
import json
from pathlib import Path
from typing import Iterable, List

from vidur.training.types import OpProfilePoint

from .schema import csv_fields, point_to_row


def write_profiles(path: Path, points: Iterable[OpProfilePoint]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields())
        writer.writeheader()
        writer.writerows(point_to_row(point) for point in points)


def write_unsupported(path: Path, points: Iterable[OpProfilePoint]) -> None:
    unsupported = [unsupported_payload(point) for point in points if not point.ok]
    path.write_text(json.dumps(unsupported, indent=2), encoding="utf-8")


def unsupported_payload(point: OpProfilePoint) -> dict:
    return {"op_name": point.op_name, "phase": point.phase, "dtype": point.dtype, "m": point.m, "n": point.n, "k": point.k, "error": point.error}


def merge_points(chunks: List[List[OpProfilePoint]]) -> List[OpProfilePoint]:
    return [point for chunk in chunks for point in chunk]
