from google import genai
from google.genai import types
import json
import os


class DamageDetector:

    def __init__(self, api_key=None):
        if not api_key:
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("Please set GOOGLE_API_KEY environment variable")

        self.client = genai.Client(api_key=api_key)

    def analyze_damage(self, pre_image_path, post_image_path):

        with open(pre_image_path, 'rb') as f:
            pre_image_bytes = f.read()

        with open(post_image_path, 'rb') as f:
            post_image_bytes = f.read()

        prompt = """You are an expert disaster damage assessment AI. Compare these two satellite images:
1. FIRST IMAGE: PRE-DISASTER (before the disaster)
2. SECOND IMAGE: POST-DISASTER (after the disaster)

Your task:
1. Identify all visible buildings in the post-disaster image
2. For each building, compare its state in pre vs post images
3. Classify each building's damage level as:
   - "no-damage": Building appears intact, no visible damage
   - "minor-damage": Minor cosmetic damage, still standing and structurally sound
   - "major-damage": Significant structural damage, roof/walls damaged but not collapsed
   - "destroyed": Building collapsed, rubble, or completely destroyed

Return ONLY a valid JSON array with this exact format (no markdown, no extra text):
[
  {
    "building_id": 1,
    "damage": "major-damage",
    "confidence": 0.85,
    "description": "Roof partially collapsed",
    "bbox": [100, 200, 300, 400]
  }
]

Rules:
- bbox coordinates in pixels (0-1024)
- confidence 0.0-1.0
- Return ONLY JSON array, no other text
"""

        try:
            print(f"Using model: gemini-2.5-flash...")
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    "PRE-DISASTER IMAGE:",
                    types.Part.from_bytes(data=pre_image_bytes, mime_type='image/png'),
                    "POST-DISASTER IMAGE:",
                    types.Part.from_bytes(data=post_image_bytes, mime_type='image/png'),
                    prompt
                ]
            )

            print(f"✓ AI analysis complete!\n")
            response_text = response.text

            # Parse JSON
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()

            damage_assessments = json.loads(json_str)
            return damage_assessments

        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            print(f"Raw response:\n{response_text}")
            return []
        except Exception as e:
            print(f"Error: {e}")
            return []


def main():
    detector = DamageDetector()

    pre_image = "./data/santa_rosa_demo/pre/santa-rosa-wildfire_00000089_pre_disaster.png"
    post_image = "./data/santa_rosa_demo/post/santa-rosa-wildfire_00000089_post_disaster.png"

    print(f"Analyzing damage for image pair...\n")

    results = detector.analyze_damage(pre_image, post_image)

    print(f"Found {len(results)} buildings:")
    for building in results:
        print(f"  Building {building['building_id']}: {building['damage']} "
              f"(confidence: {building.get('confidence', 0):.2f})")
        print(f"    {building.get('description', 'No description')}")

    output_file = "./data/ai_predictions_test.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()