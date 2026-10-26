"""Swap providers by implementing these interfaces and registering them in registry.py."""
from abc import ABC, abstractmethod


class LLMService(ABC):
    name: str
    @abstractmethod
    async def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        """Return an assistant message: {"content": str, "tool_calls": [{"function": {"name", "arguments"}}]}"""
    @abstractmethod
    async def health(self) -> dict: ...


class STTService(ABC):
    name: str
    @abstractmethod
    async def transcribe(self, path: str) -> str: ...
    @abstractmethod
    async def health(self) -> dict: ...


class TTSService(ABC):
    name: str
    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Return WAV bytes."""
    @abstractmethod
    async def health(self) -> dict: ...
