# app/pipelines/utils/parsers.py

"""
Utilidades para extraer JSON de respuestas de LLM y construir mensajes de prompt.
"""

import json
import re
from typing import Any, Dict, List, Union
from datetime import datetime
import pytz

# --- CORRECCIÓN ---
# La expresión regular ahora busca un bloque ```json que comience al
# inicio del string (con posible espacio en blanco antes).
# Esto evita que se confunda con bloques de código anidados.
_JSON_FENCE = re.compile(r"^\s*```json\s*([\s\S]*?)```\s*$", re.IGNORECASE | re.MULTILINE)

def extract_json_block(text: str) -> str:
    """
    Si el texto es un bloque de código JSON, devuelve solo su contenido.
    En caso contrario, devuelve el texto entero para un parseo directo.
    """
    m = _JSON_FENCE.search(text.strip())
    return m.group(1).strip() if m else text.strip()

def parse_payload(text: str) -> Union[Dict[str, Any], List[Any]]:
    """
    Función centralizada para limpiar y parsear una respuesta JSON de un LLM.
    """
    clean_text = extract_json_block(text)

    if not clean_text:
        raise ValueError("La respuesta del LLM estaba vacía o no contenía un bloque JSON válido.")

    return json.loads(clean_text, strict=False)

def build_prompt_messages(
    system_template: str,
    user_message_template: str,
    payload: Union[Dict[str, Any], List[Any], str],
) -> List[Dict[str, Any]]:
    """
    Construye la lista de mensajes system+user para la API del LLM,
    inyectando placeholders dinámicos de forma segura.
    """
    final_user_message_content = user_message_template

    if "{current_date_context}" in final_user_message_content:
        mexico_city_tz = pytz.timezone('America/Mexico_City')
        now = datetime.now(mexico_city_tz)
        date_context = f"La fecha y hora actual es {now.strftime('%d de %B de %Y, %H:%M:%S')} en la Ciudad de México."
        final_user_message_content = final_user_message_content.replace('{current_date_context}', date_context)

    if isinstance(payload, str):
        user_content_payload_str = payload
    else:
        user_content_payload_str = json.dumps(payload, ensure_ascii=False, indent=2)

    final_user_message_content = final_user_message_content.replace('{input}', user_content_payload_str)

    messages = []
    if system_template:
        messages.append({"role": "system", "content": system_template})
    messages.append({"role": "user", "content": final_user_message_content})

    return messages
