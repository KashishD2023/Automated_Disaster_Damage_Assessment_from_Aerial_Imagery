"""Load tile details and image paths from tiles_demo.csv."""

import csv
from pathlib import Path

from app.config import TILES_CSV_PATH
from app.schemas import TileDetail


def load_tiles(csv_path: Path | None = None) -> list[TileDetail]:
    """Read tiles from CSV; return list of TileDetail. Raises if file missing or invalid."""
    path = csv_path or TILES_CSV_PATH
    if not path.exists():
        return []
    tiles: list[TileDetail] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                tiles.append(
                    TileDetail(
                        tile_id=int(row["tile_id"]),
                        pre_disaster_path=row["pre_disaster_path"].strip(),
                        post_disaster_path=row["post_disaster_path"].strip(),
                    )
                )
            except (KeyError, ValueError):
                continue
    return tiles


def get_tile_by_id(tile_id: int, csv_path: Path | None = None) -> TileDetail | None:
    """Return a single tile by tile_id, or None if not found."""
    for t in load_tiles(csv_path):
        if t.tile_id == tile_id:
            return t
    return None
