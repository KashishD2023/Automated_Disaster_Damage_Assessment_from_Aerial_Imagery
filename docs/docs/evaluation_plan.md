# Evaluation Plan – Volcano Damage Assessment

## Purpose
The goal of the evaluation is to measure how well the model’s predicted damage classes
match the ground-truth damage labels provided by FEMA. This will allow us to understand
how accurate the system is and where it makes mistakes.

## Data Used for Evaluation
Evaluation will be done using a joined dataset that combines:
- model-predicted damage labels for each image tile
- FEMA damage labels for the same locations

Each record should contain at least:
- tile_id
- predicted_damage_class
- FEMA_damage_class
- confidence score (if available)

Any rows missing either a prediction or a FEMA label will be excluded from evaluation.

## Damage Classes
The evaluation will use the same damage classes defined by the project standards.
These classes represent increasing levels of damage caused by the volcano, such as:
- no damage
- minor damage
- major damage
- destroyed

If FEMA labels differ from the project classes, they will be mapped before evaluation.

## Evaluation Metrics

### Accuracy
Accuracy is calculated as the number of correct predictions divided by the total number
of evaluated samples.

Accuracy = (number of correct predictions) / (total predictions)

### Confusion Matrix
A confusion matrix will be created to show how predicted classes compare to FEMA labels.
Rows represent the FEMA ground truth, and columns represent the model predictions.
This helps identify which classes are commonly confused.

### Precision, Recall, and F1 Score
For each damage class:
- Precision measures how many predicted samples for a class are correct.
- Recall measures how many actual FEMA samples of a class were correctly identified.
- F1 score provides a balance between precision and recall.

These metrics will be reported per class as well as averaged across all classes.

## Handling Edge Cases
- If a damage class does not appear in the FEMA data, it will be noted in the results.
- If multiple FEMA regions overlap a single tile, the region with the largest overlap
  will be used as the ground truth.
- Low-confidence predictions may be analyzed separately to understand uncertainty.

## Outputs
The evaluation process will produce:
- a confusion matrix
- overall accuracy
- per-class precision, recall, and F1 scores

These results will be saved in the evaluation folder and summarized in a short report
for later project milestones.

## Notes
Volcano-related factors such as ash clouds, smoke, and lava flow boundaries may affect
image visibility and model performance, and these will be considered during error analysis.
