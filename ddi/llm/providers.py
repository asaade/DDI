# ddi/llm/providers.py

from __future__ import annotations
import logging
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Tuple, Literal

from ddi.core.config import settings, Settings
from .retry import make_retry # <-- CORRECCIÓN: Importa desde el nuevo archivo

from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError, AuthenticationError
from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions
import ollama
from aiohttp.client_exceptions import ClientConnectorError, ConnectionTimeoutError

log = logging.getLogger("app.llm")

ToolChoice = Literal["auto", "any", "none"]

class EmptyLLMResponseError(ValueError):
    """Excepción para cuando el LLM devuelve una respuesta vacía."""
    pass

@dataclass
class LLMResponse:
    text: str
    model: str
    usage: Dict[str, int]
    tool_calls: Optional[List[Dict[str, Any]]] = None
    parsed_data: Optional[Any] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None

_PROVIDER_REGISTRY: Dict[str, Type['BaseLLMClient']] = {}

def register_provider(name: str):
    def decorator(cls: Type['BaseLLMClient']):
        _PROVIDER_REGISTRY[name.lower()] = cls
        return cls
    return decorator

def get_provider(name: str) -> 'BaseLLMClient':
    try:
        client_cls = _PROVIDER_REGISTRY[name.lower()]
        return client_cls(settings)
    except KeyError:
        raise ValueError(f"Proveedor LLM no soportado: {name!r}")

class BaseLLMClient(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(f"app.llm.{self.__class__.__name__}")
        self._retry = make_retry(self.retry_exceptions(), settings.llm_max_retries)

    @classmethod
    def retry_exceptions(cls) -> Tuple[Type[Exception], ...]:
        return ()

    async def generate_response(self, messages: List[Dict[str, Any]], tool_choice: ToolChoice = "auto", **kwargs: Any) -> LLMResponse:
        try:
            return await self._retry(self._call)(messages, tool_choice=tool_choice, **kwargs)
        except Exception as e:
            self.logger.error(f"Error durante la llamada LLM para {self.__class__.__name__}: {e}", exc_info=True)
            return LLMResponse(text="", model=kwargs.get("model", "unknown"), usage={}, success=False, error_message=str(e))

    @abstractmethod
    async def _call(self, messages: List[Dict[str, Any]], tool_choice: ToolChoice, **kwargs: Any) -> LLMResponse:
        pass

@register_provider("gemini")
class GeminiClient(BaseLLMClient):
    @classmethod
    def retry_exceptions(cls) -> Tuple[Type[Exception], ...]:
        return (
            google_exceptions.ResourceExhausted,
            google_exceptions.InternalServerError,
            ConnectionTimeoutError,
            ClientConnectorError
        )

    def __init__(self, settings: Settings):
        super().__init__(settings)
        if not settings.google_api_key:
            raise ValueError("Para la API de Gemini, se requiere 'google_api_key'.")
        # La configuración se realiza una sola vez
        genai.configure(api_key=settings.google_api_key)

    async def _call(self, messages: List[Dict[str, Any]], tool_choice: ToolChoice, **kwargs: Any) -> LLMResponse:
        system_instruction = next((msg.get("content") for msg in messages if msg.get("role") == "system"), None)
        model_name = kwargs.get("model", settings.llm_model)
        gemini_history = self._build_gemini_history(messages)

        generation_config = types.GenerateContentConfig(
            temperature=kwargs.get("temperature", settings.llm_temperature),
            max_output_tokens=kwargs.get("max_tokens", settings.llm_max_tokens),
            safety_settings=[types.SafetySetting(category=cat, threshold=types.HarmBlockThreshold.BLOCK_NONE) for cat in (types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, types.HarmCategory.HARM_CATEGORY_HARASSMENT, types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT)],
        )

        model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
        res = await model.generate_content_async(contents=gemini_history, generation_config=generation_config)
        return self._parse_gemini_response(res, model_name)

    def _build_gemini_history(self, messages: List[Dict[str, Any]]) -> List[types.Content]:
        gemini_history = []
        for msg in messages:
            role = msg.get("role")
            if role == "system": continue
            if role == "assistant": role = "model"
            gemini_history.append(types.Content(parts=[types.Part(text=msg.get("content", ""))], role=role))
        return gemini_history

    def _parse_gemini_response(self, res: types.GenerateContentResponse, model_name: str) -> LLMResponse:
        text_content, success, error_message = "", True, None
        try:
            candidate = res.candidates[0]

            if (candidate.finish_reason == types.FinishReason.STOP and not candidate.content.parts):
                raise EmptyLLMResponseError(f"Respuesta vacía. Razón: {candidate.finish_reason.name}")

            if res.prompt_feedback and res.prompt_feedback.block_reason:
                error_message = f"Solicitud bloqueada por seguridad. Razón: {res.prompt_feedback.block_reason.name}"; success = False
            elif candidate.content and candidate.content.parts:
                text_content = "".join(part.text for part in candidate.content.parts if part.text)

        except (IndexError, AttributeError):
            success, error_message = False, f"Error al parsear la respuesta de Gemini. Raw: {res}"

        usage = {"total": res.usage_metadata.total_token_count if hasattr(res, 'usage_metadata') else 0}
        return LLMResponse(text=text_content, model=model_name, usage=usage, success=success, error_message=error_message)


async def generate_response(messages: List[Dict[str, Any]], **kwargs: Any) -> LLMResponse:
    provider_name = kwargs.pop("provider", settings.llm_provider)
    client = get_provider(provider_name)
    return await client.generate_response(messages=messages, **kwargs)
