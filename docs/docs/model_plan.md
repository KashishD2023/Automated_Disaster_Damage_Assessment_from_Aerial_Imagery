# Vision Language Model (VLM)

## Importance
One of the core components of creating an inference only pipeline is selecting an appropriate model. 
In this case, since we will be comparing many before and after images, a VLM that supports image reasoning will be the best choice for this project.

## Choosing the Model
There are many large languange model (LLM) APIs that can be used for this project. As for which one, the DeepSeek-R1 API using 
OpenRouter would be the best, as it will enable us to run the API key for free. 

Other options can be explored in case we face roadblocks with performance/compatibality, such as:
- GPT-4o
- Claude 3.5 Sonnet
- LLaVa
- Qwen-VL

Inference will be done by the following workflow:
1. Input: pass the pre-disaster and post-disaster images to the chat bot.
2. Prompting: pass a prompt to the VLM to identify any changes.
3. Output Parsing: Ensure the model returns a structured JSON format so the dashboard can read it easily.

## Prediction Field Definitions
Below is a table of prediction fields that will be used for the dashboard and evaluation process:

| Field Name      | Type    | Description                                 |
|-----------------|---------|---------------------------------------------|
| title           | String  | Unique identifier for the image title       |
| geometry        | GeoJSON | The bounding box or point for map rendering |
| predicted_class | String | Must map to FEMA labels |
| confidence_score | Float | 0.0 to 1.0, representing model certainty |
| explanation | String | Short description of the model's reasoning of its analysis |

<sub> *NOTE: These fields can be subject to change depending on project requirements.* </sub> 
