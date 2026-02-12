from google import genai
import os

api_key = os.getenv('GOOGLE_API_KEY')
if not api_key:
    print("Please set GOOGLE_API_KEY environment variable")
    exit(1)

client = genai.Client(api_key=api_key)

print("Available models:")
print("-" * 50)

try:
    models = client.models.list()
    for model in models:
        if hasattr(model, 'name'):
            print(f"  - {model.name}")
            if hasattr(model, 'supported_generation_methods'):
                print(f"    Methods: {model.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
    print("\nTrying alternative approach...")

    # Try these common models
    test_models = [
        'gemini-3-pro-preview',
        'gemini-2.0-flash',
        'gemini-1.5-pro-latest',
        'gemini-1.5-flash-latest',
        'gemini-exp-1206',
    ]

    for model_name in test_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=["Hello, test"]
            )
            print(f"✓ {model_name} - WORKS")
        except Exception as e:
            error_msg = str(e)[:100]
            print(f"✗ {model_name} - {error_msg}")