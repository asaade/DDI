# ddi/llm/tools.py
from typing import List

def web_search(query: str) -> str:
    """
    Realiza una búsqueda web y devuelve un resumen de los resultados.
    Esta es una implementación de marcador de posición.
    """
    print(f"--- EJECUTANDO HERRAMIENTA: Búsqueda Web para '{query}' ---")
    # Lógica de búsqueda real iría aquí.
    return f"Resultados de la búsqueda para '{query}': [Contenido encontrado en la web...]"

available_tools = [
    {
        "name": "web_search",
        "description": "Busca en la web para encontrar información factual, definiciones o verificar datos.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "La consulta de búsqueda precisa a ejecutar."
                }
            },
            "required": ["query"]
        }
    }
]
