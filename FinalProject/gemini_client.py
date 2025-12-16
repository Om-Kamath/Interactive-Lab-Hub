import json
import os
import time
from pathlib import Path
from string import Template
from typing import Any, Dict, Optional

from google import genai
from google.genai import types


class GeminiPlanner:
    """Wrapper around the google-genai SDK for subway routing prompts."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-3-pro-preview",
        prompt_path: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(api_key=self.api_key)
        self.model = model
        self.prompt_template = self._load_prompt_template(prompt_path)

    def _load_prompt_template(self, prompt_path: Optional[str]) -> Template:
        path = Path(prompt_path or os.environ.get("GEMINI_PROMPT_PATH", "prompt.md"))
        if not path.exists():
            raise FileNotFoundError(f"Prompt template missing at {path}")
        return Template(path.read_text(encoding="utf-8"))

    def _build_prompt(self, variables: Dict[str, Any]) -> str:
        safe_vars = {k: ("" if v is None else v) for k, v in variables.items()}
        return self.prompt_template.safe_substitute(**safe_vars)

    def _generate(self, prompt: str) -> Dict[str, Any]:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            )
        ]

        tools = []
        if hasattr(types, "UrlContext"):
            try:
                tools.append(types.Tool(url_context=types.UrlContext()))
            except Exception:
                pass
        if hasattr(types, "GoogleSearch"):
            try:
                # SDK may expect snake_case attr depending on version.
                tools.append(types.Tool(google_search=types.GoogleSearch()))
            except TypeError:
                try:
                    tools.append(types.Tool(googleSearch=types.GoogleSearch()))
                except Exception:
                    pass

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            tools=tools or None,
            thinking_config=types.ThinkingConfig(thinking_level="low")
        )

        attempts = 2
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                if response.text:
                    return json.loads(response.text)
                # Empty response but no exception; retry unless out of attempts.
                last_exc = RuntimeError("Gemini returned an empty response")
            except Exception as exc:  # Capture transient SDK/network errors
                last_exc = exc
            if attempt < attempts:
                time.sleep(0.5)
                continue
        # If we reach here, we failed all attempts.
        raise RuntimeError(f"Gemini request failed: {last_exc}")

    def plan_route(self, *, prompt_variables: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_prompt(prompt_variables)
        return self._generate(prompt)
