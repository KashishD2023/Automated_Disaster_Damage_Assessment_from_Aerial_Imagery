# Chatbot Question Types – Volcano Damage Assessment

## Purpose
The chatbot will allow users to ask questions about predicted damage caused by a volcano.
These questions focus on understanding damage levels, locations, and areas of concern.

## Supported Question Types

### 1. Area-based damage summary
Example: “Summarize the damage in this area.”
The chatbot should return the total number of tiles in the area and a breakdown by
damage class (no damage, minor, major, destroyed).

### 2. Location-specific damage
Example: “What is the damage at this location?”
Given a coordinate or selected point, the chatbot should return the predicted damage
class and confidence for the nearest tile.

### 3. Worst affected areas
Example: “Where is the worst damage?”
The chatbot should identify areas with the highest concentration of major or destroyed
damage and summarize the results.

### 4. Damage count by class
Example: “How many destroyed buildings are in this area?”
The chatbot should count and return how many tiles fall into the requested damage class.

### 5. Change after the volcano event
Example: “What changed after the volcano eruption?”
The chatbot should describe noticeable damage visible in post-event imagery compared
to pre-event imagery, such as ash coverage or structural loss.

### 6. Uncertain or low-confidence predictions
Example: “Which predictions are uncertain?”
The chatbot should identify predictions with low confidence and report how many such
cases exist in the selected area.

### 7. Comparison with FEMA data
Example: “How does the model compare to FEMA here?”
If evaluation data is available, the chatbot should summarize agreement or disagreement
between predictions and FEMA labels.

### 8. Response and prioritization
Example: “Which areas should responders prioritize?”
The chatbot should highlight areas with the most severe predicted damage to help guide
response planning.

## Response Style
Responses should be clear, concise, and easy to understand. When possible, numerical
summaries should be included, and the chatbot may suggest a follow-up question.
