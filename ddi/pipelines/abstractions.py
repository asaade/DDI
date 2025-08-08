# ddi/pipelines/abstractions.py

from __future__ import annotations
import asyncio
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from pydantic import TypeAdapter

from ddi.core.log import logger
from ddi.schemas.models import Item
# Asumimos que la capa de comunicación del LLM existirá en ddi/llm/utils.py
from ddi.llm.utils import call_llm_and_parse_json_result, call_llm_with_tools

class BaseStage(ABC):
    """Clase base abstracta para todas las etapas del pipeline."""
    def __init__(self, stage_name: str, params: Dict[str, Any], ctx: Dict[str, Any]):
        self.stage_name = stage_name
        self.params = params
        self.ctx = ctx
        self.logger = logger

    @abstractmethod
    async def execute(self, items: List[Item]) -> List[Item]:
        """
        Ejecuta la lógica de la etapa en una lista de ítems y devuelve la lista
        de ítems procesados. Es crucial que devuelva la lista para que el runner
        pueda mantener el estado actualizado.
        """
        raise NotImplementedError

class LLMStage(BaseStage):
    """
    Abstracción para etapas que realizan una única llamada al LLM por ítem.
    Maneja la orquestación de preparar-llamar-validar-procesar.
    """
    pydantic_schema: Any = None

    @abstractmethod
    def _prepare_llm_input(self, item: Item) -> str:
        """Prepara el string JSON de input para el prompt del LLM."""
        pass

    @abstractmethod
    async def _process_llm_result(self, item: Item, result: Optional[Any], tokens_used: int):
        """Procesa el resultado ya validado (o los errores) de la llamada al LLM."""
        pass

    async def _execute_single_item(self, item: Item) -> Item:
        """Orquesta el flujo para un solo ítem."""
        prompt_name = self.params.get("prompt")
        if not prompt_name:
            raise ValueError(f"La etapa '{self.stage_name}' no tiene un 'prompt' válido.")

        user_input = self._prepare_llm_input(item)

        validated_obj, errors, tokens_used = await call_llm_and_parse_json_result(
            prompt_name=prompt_name,
            user_input_content=user_input,
            stage_name=self.stage_name,
            item=item,
            ctx=self.ctx,
            expected_schema=self.pydantic_schema,
            **self.params
        )

        result_to_process = errors if errors else validated_obj
        await self._process_llm_result(item, result_to_process, tokens_used)

        # Devolvemos explícitamente el ítem (potencialmente modificado)
        return item

    async def execute(self, items: List[Item]) -> List[Item]:
        tasks = [self._execute_single_item(item) for item in items]
        # Recolectamos los ítems procesados para asegurar que los cambios se propaguen
        processed_items = await asyncio.gather(*tasks)
        return processed_items

class BaseAgentStage(BaseStage):
    """Abstracción para etapas que operan como agentes con herramientas (ej. búsqueda web)."""
    pydantic_schema: Any = None
    tools: List[Any] = []

    @abstractmethod
    def _prepare_llm_input(self, item: Item) -> str:
        """Prepara el string JSON de input para el prompt del agente."""
        pass

    @abstractmethod
    async def _process_llm_result(self, item: Item, result: Optional[Any], tokens_used: int):
        """Procesa el juicio final (o los errores) del agente."""
        pass

    async def _execute_single_item(self, item: Item) -> Item:
        """Orquesta el flujo de agente para un solo ítem."""
        prompt_name = self.params.get("prompt")
        if not prompt_name:
            raise ValueError(f"La etapa de agente '{self.stage_name}' no tiene un 'prompt' válido.")

        user_input = self._prepare_llm_input(item)

        validated_obj, errors, tokens_used = await call_llm_with_tools(
            prompt_name=prompt_name,
            user_input_content=user_input,
            stage_name=self.stage_name,
            item=item,
            ctx=self.ctx,
            expected_schema=self.pydantic_schema,
            tools=self.tools,
            **self.params
        )

        result_to_process = errors if errors else validated_obj
        await self._process_llm_result(item, result_to_process, tokens_used)

        return item

    async def execute(self, items: List[Item]) -> List[Item]:
        tasks = [self._execute_single_item(item) for item in items]
        processed_items = await asyncio.gather(*tasks)
        return processed_items
