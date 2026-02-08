import asyncio
import json
import re
from typing import TYPE_CHECKING, Any

from google.genai import Client, types

from src.core.config import settings
from src.core.logging import get_logger

if TYPE_CHECKING:
    from google.genai.types import GenerateContentResponse

logger = get_logger(__name__)


def _repair_json(text: str) -> str:
    """
    Attempt to repair common JSON issues from AI-generated responses.

    Handles:
    - Unterminated strings (adds closing quote)
    - Missing closing brackets/braces
    - Trailing commas
    """
    text = re.sub(r",\s*([}\]])", r"\1", text)

    open_braces = text.count("{") - text.count("}")
    open_brackets = text.count("[") - text.count("]")

    in_string = False
    escape_next = False
    escape_next = False

    for _i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string

    if in_string:
        text = text + '"'
        logger.debug("Repaired: Added closing quote for unterminated string")

    if open_brackets > 0:
        text = text.rstrip(",\n\t ")
        text = text + ("]" * open_brackets)
        logger.debug(f"Repaired: Added {open_brackets} closing bracket(s)")

    if open_braces > 0:
        text = text.rstrip(",\n\t ")
        text = text + ("}" * open_braces)
        logger.debug(f"Repaired: Added {open_braces} closing brace(s)")

    return text


class AIService:
    """
    AI Service for generating content using Google Gemini.

    Note: Creates a new Client per request to avoid event loop issues
    when used with Celery's asyncio.run() which creates fresh event loops.
    """

    async def generate(self, prompt: str) -> dict:
        client = Client(api_key=settings.GOOGLE_API_KEY)
        max_retries = 2
        timeout_seconds = 120

        for attempt in range(max_retries):
            try:
                response: GenerateContentResponse = await asyncio.wait_for(
                    client.aio.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.0,
                            candidate_count=1,
                            top_p=0.95,
                            top_k=5,
                            presence_penalty=0.0,
                            frequency_penalty=0.0,
                        ),
                    ),
                    timeout=timeout_seconds,
                )
                text_response: str = response.text.strip()  # ty:ignore[possibly-missing-attribute]

                if text_response.startswith("```json"):
                    text_response: str = text_response[7:-3].strip()
                elif text_response.startswith("```"):
                    text_response: str = text_response[3:-3].strip()

                try:
                    data: dict[str, Any] = json.loads(text_response)
                    return data
                except json.JSONDecodeError as parse_error:
                    logger.warning(f"Initial JSON parse failed: {parse_error}. Attempting repair...")
                    repaired_text = _repair_json(text_response)
                    try:
                        data = json.loads(repaired_text)
                        logger.info("JSON repair successful")
                        return data
                    except json.JSONDecodeError:
                        raise parse_error

            except TimeoutError:
                logger.warning(
                    f"AI generation timed out after {timeout_seconds}s. Retrying ({attempt + 1}/{max_retries})..."
                )
                if attempt == max_retries - 1:
                    raise RuntimeError(f"AI generation failed after {max_retries} attempts due to timeout")
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"AI generation failed: {e!s}")

                logger.warning(f"AI generation failed with error: {e}. Retrying ({attempt + 1}/{max_retries})...")
                await asyncio.sleep(1)

        raise RuntimeError("AI generation failed unexpectedly")


ai_service = AIService()
