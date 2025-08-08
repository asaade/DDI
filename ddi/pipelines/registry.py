# ddi/pipelines/registry.py

from typing import Dict, Type
from ddi.pipelines.abstractions import BaseStage

# El registro es un simple diccionario que mapea un nombre (string)
# a una clase de etapa.
_stage_registry: Dict[str, Type[BaseStage]] = {}

def register(stage_name: str):
    """
    Decorador que registra una clase de etapa en el registro central.

    Permite que el runner encuentre la clase de una etapa a partir del
    nombre especificado en el archivo pipeline.yml.

    Uso:
        @register("nombre_de_la_etapa")
        class MiEtapa(BaseStage):
            ...
    """
    def decorator(cls: Type[BaseStage]):
        if stage_name in _stage_registry:
            raise ValueError(f"La etapa '{stage_name}' ya ha sido registrada.")
        _stage_registry[stage_name] = cls
        return cls
    return decorator

def get_full_registry() -> Dict[str, Type[BaseStage]]:
    """
    Devuelve una copia del registro completo de etapas.
    """
    return _stage_registry.copy()
