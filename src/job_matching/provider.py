"""Minimal provider interface and classified failures."""
from typing import Protocol


class ProviderError(RuntimeError):
    """Permanent provider rejection; do not retry."""


class TransientProviderError(ProviderError):
    """Temporary network, quota, or server failure."""


class AIProvider(Protocol):
    def generate(self, prompt: str) -> str: ...
