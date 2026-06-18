from plugins.ai_gen.backends.base import ImageGenerator, GenerationError

BACKENDS = {}


def register_backend(name: str):
    """Decorator that registers an ImageGenerator subclass under a CLI name."""
    def wrapper(cls):
        BACKENDS[name] = cls
        return cls
    return wrapper


def get_backend(name: str) -> ImageGenerator:
    """Instantiate a registered backend by name.

    Backends are imported lazily so that optional dependencies (e.g. the
    ``openai`` SDK) are only required when that backend is actually used.
    """
    # Import for their registration side effects.
    from plugins.ai_gen.backends import openai_backend  # noqa: F401
    from plugins.ai_gen.backends import browser_backend  # noqa: F401

    if name not in BACKENDS:
        available = ', '.join(sorted(BACKENDS)) or '(none)'
        raise GenerationError(f'Unknown backend "{name}". Available backends: {available}.')

    return BACKENDS[name]()


def get_backend_names() -> list:
    """Return the list of registered backend names (for Click choices)."""
    from plugins.ai_gen.backends import openai_backend  # noqa: F401
    from plugins.ai_gen.backends import browser_backend  # noqa: F401
    return sorted(BACKENDS)
