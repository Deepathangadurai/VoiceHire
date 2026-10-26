import httpx
from ..config import VoiceSettings
from ..errors import ServiceError
from .base import LLMService


class OllamaLLM(LLMService):
    name = "ollama"

    def __init__(self, s: VoiceSettings):
        self.s = s

    def _client(self, timeout: float | None = None) -> httpx.AsyncClient:
        t = httpx.Timeout(timeout or self.s.llm_timeout_seconds, connect=3)
        return httpx.AsyncClient(base_url=self.s.ollama_base_url, timeout=t)

    async def chat(self, messages: list[dict], tools: list[dict]) -> dict:
        s = self.s
        body = {"model": s.ollama_model, "messages": messages, "stream": False, "keep_alive": s.llm_keep_alive,
                "options": {"temperature": s.llm_temperature}}
        if tools:
            body["tools"] = tools
        try:
            async with self._client() as c:
                r = await c.post("/api/chat", json=body)
        except httpx.ConnectError:
            raise ServiceError("llm_unavailable", f"Ollama is not running at {s.ollama_base_url}. Start the Ollama app or run `ollama serve`.")
        except httpx.TimeoutException:
            raise ServiceError("llm_timeout", "The local model took too long to answer. Try a smaller OLLAMA_MODEL or a shorter question.", 504)
        except httpx.HTTPError:
            raise ServiceError("llm_unavailable", "Could not talk to Ollama.")
        if r.status_code == 404:
            raise ServiceError("llm_model_missing", f"Model '{s.ollama_model}' is not installed. Run: ollama pull {s.ollama_model}")
        if r.status_code == 400 and "tool" in r.text.lower():
            raise ServiceError("llm_no_tools", f"Model '{s.ollama_model}' does not support tool calling. Try llama3.2:3b, qwen2.5:7b or llama3.1:8b.")
        if r.status_code >= 400:
            raise ServiceError("llm_error", f"Ollama returned HTTP {r.status_code}.", 502)
        return r.json().get("message") or {"role": "assistant", "content": ""}

    async def health(self) -> dict:
        s = self.s
        try:
            async with self._client(3) as c:
                r = await c.get("/api/tags")
            names = {m.get("name", "") for m in r.json().get("models", [])}
        except Exception:
            return {"ok": False, "provider": self.name, "detail": f"Ollama is not running at {s.ollama_base_url}."}
        want = s.ollama_model
        if want in names or (":" not in want and f"{want}:latest" in names):
            return {"ok": True, "provider": self.name, "model": want, "detail": "ready"}
        return {"ok": False, "provider": self.name, "model": want, "detail": f"Model not installed. Run: ollama pull {want}"}
