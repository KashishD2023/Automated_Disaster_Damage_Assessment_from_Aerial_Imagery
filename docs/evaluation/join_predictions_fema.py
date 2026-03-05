from pathlib import Path
import pandas as pd
import geopandas as gpd

# 🔹 Adjusted to match your current repo structure
PRED_PATH = Path("model/predictions_demo.geojson")   
FEMA_PATH = Path("data/raw/fema/fema_labels.geojson")  # FEMA file (pending)
OUT_PATH  = Path("data/processed/joined_demo.csv")

# Possible column names (handles variations)
PRED_CLASS_COL_CANDIDATES = ["damage_class", "pred_class", "class"]
FEMA_CLASS_COL_CANDIDATES = ["damage_class", "fema_class", "subtype", "label"]

# Severity rule for tie-breaking
SEVERITY = {
    "NO_DAMAGE": 0,
    "MINOR": 1,
    "MAJOR": 2,
    "DESTROYED": 3,
    "UNKNOWN": -1
}

def pick_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(f"None of these columns exist: {candidates}. Found: {list(df.columns)}")

def normalize_label(x):
    if not isinstance(x, str):
        return "UNKNOWN"
    t = x.strip().upper()
    t = t.replace("NONE", "NO_DAMAGE")
    t = t.replace("NO DAMAGE", "NO_DAMAGE")
    t = t.replace("NODAMAGE", "NO_DAMAGE")
    t = t.replace("DESTROY", "DESTROYED")
    if t not in SEVERITY:
        return "UNKNOWN"
    return t

def max_severity(labels):
    labels = [normalize_label(x) for x in labels]
    real = [x for x in labels if x != "UNKNOWN"]
    labels = real if real else labels
    return max(labels, key=lambda k: SEVERITY.get(k, -1))

def main():
    if not PRED_PATH.exists():
        print(f"[BLOCKED] Missing predictions file: {PRED_PATH}")
        return

    if not FEMA_PATH.exists():
        print(f"[BLOCKED] Missing FEMA file: {FEMA_PATH}")
        print("Waiting on FEMA labels to generate joined_demo.csv")
        return

    pred = gpd.read_file(PRED_PATH)
    fema = gpd.read_file(FEMA_PATH)

    if "tile_id" not in pred.columns:
        raise ValueError("Predictions file must include tile_id")

    pred_class_col = pick_col(pred, PRED_CLASS_COL_CANDIDATES)
    fema_class_col = pick_col(fema, FEMA_CLASS_COL_CANDIDATES)

    # Normalize CRS to EPSG:4326
    pred = pred.to_crs("EPSG:4326") if pred.crs else pred.set_crs("EPSG:4326")
    fema = fema.to_crs("EPSG:4326") if fema.crs else fema.set_crs("EPSG:4326")

    pred = pred[pred.geometry.notnull()].copy()
    fema = fema[fema.geometry.notnull()].copy()

    # Spatial join
    joined = gpd.sjoin(
        pred[["tile_id", pred_class_col, "geometry"]],
        fema[[fema_class_col, "geometry"]],
        how="left",
        predicate="intersects",
    )

    # Collapse to one row per tile_id
    agg = (
        joined.groupby("tile_id")
        .agg(
            pred_class=(pred_class_col, lambda s: normalize_label(s.iloc[0])),
            fema_class=(fema_class_col, lambda s: max_severity(list(s.dropna())) if len(s.dropna()) else "UNKNOWN"),
        )
        .reset_index()
    )

    agg["match_flag"] = (agg["fema_class"] != "UNKNOWN").astype(int)
    agg["join_method"] = "spatial"

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(OUT_PATH, index=False)

    print(f"✅ Wrote {len(agg)} rows to {OUT_PATH}")

if __name__ == "__main__":
    main()
