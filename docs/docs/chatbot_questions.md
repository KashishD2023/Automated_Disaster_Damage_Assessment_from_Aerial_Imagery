# Chatbot Question Types - Santa Rosa Wildfire Damage Assessment

## Purpose
The chatbot allows users to ask questions about predicted building damage caused by the Santa Rosa wildfire using pre- and post-disaster aerial imagery.  
These questions help users understand damage levels, affected locations, and areas that may require response or further investigation.

## Supported Question Types

### 1. Area-based damage summary
Example: “Summarize the damage in this area.”

The chatbot should return the total number of tiles or buildings in the selected area and provide a breakdown by predicted damage class (no damage, minor damage, major damage, destroyed).

### 2. Location-specific damage
Example: “What is the damage at this location?”

Given a coordinate, selected point on the map, or tile ID, the chatbot should return the predicted damage class and confidence score for the nearest tile or building.

### 3. Worst affected areas
Example: “Where is the worst damage?”

The chatbot should identify areas with the highest concentration of major or destroyed damage and summarize the results.

### 4. Damage count by class
Example: “How many destroyed buildings are in this area?”

The chatbot should count and return the number of tiles or buildings that fall into the requested damage class.

### 5. Change after the wildfire event
Example: “What changed after the wildfire?”

The chatbot should describe visible changes between pre-disaster and post-disaster imagery, such as burned structures, structural loss, or other visible wildfire damage.

### 6. Uncertain or low-confidence predictions
Example: “Which predictions are uncertain?”

The chatbot should identify predictions with low confidence scores and report how many such cases exist in the selected area.

### 7. Comparison with FEMA data
Example: “How do the model predictions compare to FEMA damage labels here?”

If FEMA ground-truth labels are available, the chatbot should summarize agreement or disagreement between model predictions and FEMA data.

### 8. Response and prioritization
Example: “Which areas should responders prioritize?”

The chatbot should highlight areas with the most severe predicted damage to help guide response planning.

## Response Style
Responses should be clear, concise, and easy to understand. When possible, numerical summaries should be included.  
The chatbot may also suggest a follow-up question that helps the user explore damage patterns in more detail.

---

## Week 2 – Chatbot Backend & Evaluation Integration (Person 6)

### Objective
Define how the chatbot will interact with backend data and how its outputs will later be evaluated against FEMA damage labels.

### Backend Data Usage
The chatbot will retrieve the following information from backend data sources:

- Tile ID  
- Predicted damage class  
- Confidence score  
- FEMA damage label (when available)  
- Associated pre-disaster and post-disaster imagery  

### Planned Chatbot Flow
1. A user submits a damage-related question.
2. The chatbot identifies the question type (area-based, tile-based, or comparison).
3. The chatbot queries backend data sources.
4. The chatbot formats a human-readable response based on the available data.

### Evaluation Considerations
Chatbot responses rely on model predictions that will later be evaluated using:

- Accuracy  
- Confusion matrix  
- Precision and recall  
- Comparison with FEMA ground-truth labels  

### Week 2 Status
This section documents the planned chatbot integration and evaluation design.  
No backend queries or evaluation code have been implemented yet.

