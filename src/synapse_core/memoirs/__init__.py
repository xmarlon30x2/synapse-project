"""
Paquete de Memorias - Sistemas de Persistencia del Agente

Provee implementaciones de memoria para almacenar y recuperar el historial
de conversaciones, incluyendo mensajes del usuario, respuestas del asistente
y resultados de herramientas ejecutadas.

Implementaciones disponibles:
- JSONFileMemory: Almacenamiento en archivo JSON local
- SummarizingJSONFileMemory: Almacenamiento con capacidad de resumen
- Memory: Interfaz abstracta para nuevas implementaciones
"""

from .json_file_memory import JSONFileMemory
from .memory import Memory
from .summarizing_json_file_memory import SummarizingJSONFileMemory

__all__ = ["Memory", "JSONFileMemory", "SummarizingJSONFileMemory"]
