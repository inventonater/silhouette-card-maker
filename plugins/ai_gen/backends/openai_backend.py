import base64
import os
from contextlib import ExitStack
from typing import List, Optional

from plugins.ai_gen.backends import register_backend
from plugins.ai_gen.backends.base import ImageGenerator, GenerationError

MODEL = "gpt-image-2"


@register_backend("openai")
class OpenAIImageGenerator(ImageGenerator):
    """Image generation backed by the official OpenAI Images API (gpt-image-2).

    Reproduces the ChatGPT "Pro Extended" experience: ``thinking`` reasoning,
    ``n`` parallel variations sharing a style, optional reference-image editing,
    and print-quality output. Requires the ``openai`` package and an
    ``OPENAI_API_KEY`` environment variable.
    """

    def __init__(self):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise GenerationError(
                'The "openai" package is required for the openai backend. '
                'Install it with `pip install openai` (or `pip install -r requirements.txt`).'
            ) from e

        if not os.environ.get('OPENAI_API_KEY'):
            raise GenerationError(
                'OPENAI_API_KEY is not set. Export your API key, e.g. '
                '`export OPENAI_API_KEY=sk-...`, before generating.'
            )

        self._client = OpenAI()

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
        # `thinking` is a gpt-image-2 parameter that may not yet be modeled by
        # the installed SDK, so pass it through the documented extra_body escape
        # hatch rather than as a typed kwarg.
        extra_body = {"thinking": thinking} if thinking else {}

        try:
            if reference_images:
                with ExitStack() as stack:
                    handles = [stack.enter_context(open(p, 'rb')) for p in reference_images]
                    response = self._client.images.edit(
                        model=MODEL,
                        image=handles,
                        prompt=prompt,
                        n=n,
                        size=size,
                        quality=quality,
                        extra_body=extra_body,
                    )
            else:
                response = self._client.images.generate(
                    model=MODEL,
                    prompt=prompt,
                    n=n,
                    size=size,
                    quality=quality,
                    extra_body=extra_body,
                )
        except Exception as e:  # surface a clean error to the CLI
            raise GenerationError(f'OpenAI image generation failed: {e}') from e

        return [self._decode(item) for item in (response.data or [])]

    def _decode(self, item) -> bytes:
        b64 = getattr(item, 'b64_json', None)
        if b64:
            return base64.b64decode(b64)

        # Fallback: some configurations return a URL instead of inline bytes.
        url = getattr(item, 'url', None)
        if url:
            import requests
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            return r.content

        raise GenerationError('OpenAI response contained no image data.')
