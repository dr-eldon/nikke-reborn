"""Shared error type for the card pipeline."""


class GenerationError(RuntimeError):
    """A card definition could not be rendered or composed."""
