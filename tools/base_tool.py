from abc import ABC, abstractmethod

class Tool(ABC):
    """Abstract base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool."""
        pass

    @abstractmethod
    def execute(self, **kwargs):
        """Executes the tool with the given arguments."""
        pass
