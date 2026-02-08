"""Gemini AI client with high/low model support."""

from functools import lru_cache

from google import genai

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class GeminiClient:
    """Gemini AI client with high/low model support."""

    def __init__(self):
        """Initialize Gemini client with API key."""
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self.model_high = settings.GEMINI_MODEL_HIGH
        self.model_low = settings.GEMINI_MODEL_LOW
        logger.info(f"Gemini client initialized (high: {self.model_high}, low: {self.model_low})")

    async def generate_content(self, prompt: str, use_high_priority: bool = False) -> str:
        """
        Generate content using appropriate Gemini model.

        Args:
            prompt: The prompt to send to Gemini
            use_high_priority: If True, use high priority model (Gemini Pro)
                             If False, use low priority model (Gemini Flash)

        Returns:
            Generated text response

        Raises:
            Exception: If Gemini API call fails
        """
        model_name = self.model_high if use_high_priority else self.model_low

        try:
            logger.debug(f"Calling Gemini API (model: {model_name})")

            # Use async API with new google.genai client
            response = await self.client.aio.models.generate_content(model=model_name, contents=prompt)

            # Check for valid response object
            if not response:
                raise ValueError("No response received from Gemini API")

            # Check for error responses before accessing .text
            # The new google.genai SDK can return response objects with errors embedded
            try:
                text = response.text
            except AttributeError as e:
                logger.error(f"Invalid response structure from Gemini API: {response}")
                raise ValueError(f"Invalid Gemini API response structure: {e}") from e

            if not text:
                raise ValueError("Empty response text from Gemini API")

            logger.debug(f"Gemini API response received (length: {len(text)})")
            return text.strip()

        except Exception as e:
            logger.error(f"Gemini API error (model: {model_name}): {e}")
            raise


@lru_cache(maxsize=1)
def get_gemini_client() -> GeminiClient:
    """Get singleton Gemini client instance."""
    return GeminiClient()


# Convenience singleton
gemini_client = get_gemini_client()
