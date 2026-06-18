import json
import os
import re
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator

# Allowed characters for a card id (used directly as a folder name).
_ID_RE = re.compile(r'^[A-Za-z0-9_-]+$')


class Defaults(BaseModel):
    """Default generation settings applied to every card unless overridden."""
    variations: int = Field(default=8, ge=1, le=10)
    size: str = "1024x1536"
    quality: str = "high"
    thinking: str = "high"

    model_config = {"extra": "forbid"}


class CardSpec(BaseModel):
    """A single card to generate, with optional per-card overrides."""
    id: str
    prompt: str
    reference: Optional[Union[str, List[str]]] = None
    variations: Optional[int] = Field(default=None, ge=1, le=10)
    size: Optional[str] = None
    quality: Optional[str] = None
    thinking: Optional[str] = None

    model_config = {"extra": "forbid"}

    @field_validator('id')
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not _ID_RE.match(v):
            raise ValueError(
                f'Invalid card id "{v}". Use only letters, numbers, hyphens, and underscores.'
            )
        return v

    @field_validator('prompt')
    @classmethod
    def _validate_prompt(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Card prompt must not be empty.')
        return v

    def reference_paths(self, base_dir: str) -> List[str]:
        """Reference image paths resolved relative to the spec file's directory."""
        if not self.reference:
            return []
        refs = [self.reference] if isinstance(self.reference, str) else self.reference
        resolved = []
        for r in refs:
            path = r if os.path.isabs(r) else os.path.join(base_dir, r)
            resolved.append(path)
        return resolved


class ResolvedCard:
    """A card with defaults merged in and reference paths resolved."""

    def __init__(self, card: CardSpec, defaults: Defaults, base_dir: str):
        self.id = card.id
        self.prompt = card.prompt
        self.variations = card.variations if card.variations is not None else defaults.variations
        self.size = card.size or defaults.size
        self.quality = card.quality or defaults.quality
        self.thinking = card.thinking or defaults.thinking
        self.reference_images = card.reference_paths(base_dir)


class Spec(BaseModel):
    """A full card-generation spec: shared defaults plus a list of cards."""
    defaults: Defaults = Field(default_factory=Defaults)
    cards: List[CardSpec]

    model_config = {"extra": "forbid"}

    @field_validator('cards')
    @classmethod
    def _validate_cards(cls, v: List[CardSpec]) -> List[CardSpec]:
        if not v:
            raise ValueError('Spec must contain at least one card.')
        seen = set()
        for card in v:
            if card.id in seen:
                raise ValueError(f'Duplicate card id "{card.id}". Card ids must be unique.')
            seen.add(card.id)
        return v

    def resolved_cards(self, base_dir: str) -> List[ResolvedCard]:
        return [ResolvedCard(card, self.defaults, base_dir) for card in self.cards]


def load_spec(path: str) -> Spec:
    """Load and validate a JSON spec file."""
    with open(path, 'r') as f:
        data = json.load(f)
    return Spec.model_validate(data)
