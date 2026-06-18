from typing import List, Optional

from plugins.ai_gen.backends import register_backend
from plugins.ai_gen.backends.base import ImageGenerator, GenerationError


@register_backend("browser")
class BrowserImageGenerator(ImageGenerator):
    """Placeholder backend for driving chatgpt.com directly.

    This seam exists so a browser-automation backend (e.g. Playwright against a
    logged-in ChatGPT session, using the subscription instead of API billing)
    can be added later without changing the rest of the pipeline. It is not
    implemented: the official ``openai`` backend already reproduces the
    "Pro Extended" features (thinking, n variations, reference editing).
    """

    def generate(
        self,
        prompt: str,
        n: int,
        *,
        size: str,
        quality: str,
        thinking: str,
        reference_images: Optional[List[str]] = None,
    ) -> List[bytes]:
        raise GenerationError(
            'The "browser" backend is not implemented yet. '
            'Use the "openai" backend (default), which reproduces the '
            '"Pro Extended" features via the gpt-image-2 API. '
            'See plugins/ai_gen/backends/browser_backend.py to implement '
            'browser automation if you need to use your ChatGPT subscription.'
        )
