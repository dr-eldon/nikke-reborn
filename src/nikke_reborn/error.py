"""Shared error types for the commands."""


class GenerationError(RuntimeError):
    """An input could not be found or read."""


class PublishError(RuntimeError):
    """A Nexus Mods API or network call failed."""
