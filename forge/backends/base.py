"""Backend interface for prompt generators."""
from abc import ABC, abstractmethod


class BackendError(RuntimeError):
    """Raised when a generator backend cannot produce output."""


class PromptBackend(ABC):
    name = "base"

    @abstractmethod
    def generate(self, system, user):
        """Return raw model text for the given system/user messages."""
