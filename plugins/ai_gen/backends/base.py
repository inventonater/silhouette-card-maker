from abc import ABC, abstractmethod
from typing import List, Optional


class GenerationError(Exception):
    """Raised when an image generation backend fails."""


class ImageGenerator(ABC):
    """Pluggable image generation backend.

    Implementations turn a single text prompt (plus optional reference images)
    into ``n`` candidate images, returned as raw PNG bytes. This is the seam
    that lets us swap the official OpenAI API for, e.g., a browser-automation
    backend later without touching the rest of the pipeline.
    """

    @abstractmethod
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
        """Generate ``n`` candidate images for ``prompt``.

        Args:
            prompt: The text prompt describing the desired card.
            n: How many variations to produce.
            size: Output size, e.g. "1024x1536". Backend-specific values allowed.
            quality: Quality tier, e.g. "low" / "medium" / "high".
            thinking: Reasoning effort, e.g. "off" / "low" / "medium" / "high".
            reference_images: Optional paths to reference images to edit/condition on.

        Returns:
            A list of PNG-encoded image byte strings, length up to ``n``.
        """
        raise NotImplementedError
