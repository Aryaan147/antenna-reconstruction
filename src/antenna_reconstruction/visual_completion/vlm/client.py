import os
import base64
from typing import Optional, Dict

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

from .prompts import VLM_SYSTEM_PROMPT, build_vlm_user_prompt

VLM_MODEL = os.getenv("ANTENNA_VLM_MODEL", "qwen/qwen3.8-27b")

def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def analyze_figure(figure_path: str, parameters: Dict[str, float]) -> Optional[str]:
    """Send figure and parameters to the Groq VLM and return the raw JSON string."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY environment variable not set. VLM analysis skipped.")
        return None

    try:
        client = Groq(api_key=api_key)
        base64_image = _encode_image(figure_path)
        
        # Determine media type
        ext = os.path.splitext(figure_path)[1].lower()
        if ext == ".png":
            media_type = "image/png"
        elif ext in (".jpg", ".jpeg"):
            media_type = "image/jpeg"
        elif ext == ".webp":
            media_type = "image/webp"
        else:
            media_type = "image/png" # fallback

        user_content = build_vlm_user_prompt(parameters)

        messages = [
            {
                "role": "system",
                "content": VLM_SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_content
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ]

        chat_completion = client.chat.completions.create(
            messages=messages,
            model=VLM_MODEL,
            temperature=0.0, # Deterministic output
            max_tokens=1024,
            response_format={"type": "json_object"}
        )

        return chat_completion.choices[0].message.content

    except Exception as e:
        print(f"VLM API request failed: {e}")
        return None
