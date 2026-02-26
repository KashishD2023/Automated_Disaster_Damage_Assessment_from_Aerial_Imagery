from pathlib import Path
import pandas as pd

JOINED_PATH = Path("data/processed/joined_demo.csv")
OUT_PATH = Path("evaluation/results_week4.md")

CLASSES = ["NO_DAMAGE", "MINOR", "MAJOR", "DESTROYED", "UNKNOWN"]

def confusion_matrix(y_true, y_pred, labels):
    matrix = pd.DataFrame(0, index=labels, columns=labels)
    for t, p in zip(y_true, y_pred):
        if t not in labels:
            t = "UNKNOWN"
        if p not in labels:
            p = "UNKNOWN"
        matrix.loc[t, p] += 1
    return matrix

def safe_div(a, b):
    return a / b if b != 0 else 0.0

def compute_metrics(cm, labels):
    total = cm.values.sum()
    correct = sum(cm.loc[l, l] for l in labels)
    accuracy = safe_div(correct, total)

    per_class = {}
    for c in labels:
        tp = cm.loc[c, c]
        fp = cm[c].sum() - tp
        fn = cm.loc[c].sum() - tp

        precision = safe_div(tp, tp + fp)
        recall = safe_div(tp, tp + fn)
        f1 = safe_div(2 * precision * recall, precision + recall) if (precision + recall) else 0.0

        per_class[c] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": int(cm.loc[c].sum())
        }

    return accuracy, per_class

def main():
    if not JOINED_PATH.exists():
        print(f"[BLOCKED] {JOINED_PATH} not found.")
        print("Run join_predictions_fema.py once FEMA labels are available.")
        return

    df = pd.read_csv(JOINED_PATH)

    required_cols = {"tile_id", "pred_class", "fema_class"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in joined file: {missing}")

    y_true = df["fema_class"].astype(str).str.upper().tolist()
    y_pred = df["pred_class"].astype(str).str.upper().tolist()

    cm = confusion_matrix(y_true, y_pred, CLASSES)
    accuracy, per_class = compute_metrics(cm, CLASSES)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("# Week 4 Evaluation Results\n\n")
        f.write(f"Tiles evaluated: {len(df)}\n\n")
        f.write("## Confusion Matrix (Rows=True, Columns=Predicted)\n\n")
        f.write(cm.to_markdown())
        f.write("\n\n## Metrics\n\n")
        f.write(f"Accuracy: {accuracy:.4f}\n\n")
        f.write("### Per Class Metrics\n")
        for c, m in per_class.items():
            f.write(
                f"- {c}: precision={m['precision']:.4f}, "
                f"recall={m['recall']:.4f}, "
                f"f1={m['f1']:.4f}, "
                f"support={m['support']}\n"
            )

    print(f"Results written to {OUT_PATH}")

if __name__ == "__main__":
    main()
