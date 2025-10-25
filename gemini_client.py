# gemini_client.py (patched)
import os
from typing import Optional, Dict, Any, Union, List

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_API_KEY = os.getenv("GEMINI_API_KEY")
_DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
_client: Optional[genai.Client] = None

def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not _API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Put it in your .env like:\n"
                "GEMINI_API_KEY=your_real_api_key_here"
            )
        _client = genai.Client(api_key=_API_KEY)
    return _client

def ask(
    prompt: Union[str, List[Dict[str, Any]]],
    *,
    model: str = _DEFAULT_MODEL,
    max_output_tokens: int = 1024,
    temperature: float = 0.7,
    safety_settings: Optional[Dict[str, Any]] = None,
) -> str:
    client = _get_client()

    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        # ↓ the SDK expects a GenerateContentConfig in `config`
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            safety_settings=safety_settings,  # optional
        ),
    )
    return getattr(resp, "text", str(resp))

def ask_json(
    prompt: str,
    *,
    model: str = _DEFAULT_MODEL,
    schema: types.Schema,
    temperature: float = 0.4,
    max_output_tokens: int = 1024,
):
    client = _get_client()
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    # The SDK often gives .parsed when JSON is requested; fall back to parsing text.
    if hasattr(resp, "parsed"):
        return resp.parsed
    import json
    return json.loads(getattr(resp, "text", str(resp)))

if __name__ == "__main__":
    import sys
    user_prompt = "Say 'pong' if you can read this." if len(sys.argv) < 2 else " ".join(sys.argv[1:])
    print(ask(user_prompt))