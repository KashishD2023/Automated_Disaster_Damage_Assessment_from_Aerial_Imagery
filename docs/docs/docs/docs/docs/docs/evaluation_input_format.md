# Evaluation Input Format – Week 3

This document describes the expected input format for the evaluation module after predictions are joined with FEMA ground-truth labels.

---

## Required Fields
Each row in the evaluation input file should contain the following fields:

- tile_id: Unique identifier for each image tile
- pred_class: Model-predicted damage classification
- fema_class: FEMA-provided ground-truth damage label

---

## Optional Fields
The following fields may be included to support extended analysis:

- confidence: Model confidence score for the prediction
- geometry: Spatial geometry used for filtering or visualization

---

## Notes
Evaluation metrics will compare the predicted damage class (`pred_class`) with the FEMA label (`fema_class`).  
Rows with missing or invalid labels may be excluded from metric calculations.
