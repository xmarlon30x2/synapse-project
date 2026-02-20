"""
SummarizingJSONFileMemory - Implementación de Memoria con Resumen

Esta implementación extiende JSONFileMemory añadiendo funcionalidad de resumen
de conversaciones largas para mantener la memoria eficiente y enfocada.
"""

from pathlib import Path

from ..types import AssistantMessage, Message, MessageRole
from .json_file_memory import JSONFileMemory


class SummarizingJSONFileMemory(JSONFileMemory):
    """
    Implementación de memoria que guarda los mensajes en un archivo JSON
    con capacidad de resumir conversaciones largas.
    """

    def __init__(
        self, filename: Path, max_messages: int = 1000, summary_threshold: int = 500
    ) -> None:
        super().__init__(filename)
        self.max_messages: int = max_messages
        self.summary_threshold: int = summary_threshold

    async def add(self, message: Message) -> None:
        """Añade un nuevo mensaje y gestiona el resumen si es necesario."""
        await super().add(message)

        # Comprobar si necesitamos resumir
        if len(self.messages) > self.summary_threshold:
            await self._create_summary()

    async def _create_summary(self) -> None:
        """Crea un resumen de la conversación y mantiene solo los mensajes recientes."""

        # Obtener mensajes recientes
        recent_messages = await self.get_history(self.max_messages)

        # Crear resumen (en una implementación real, usaríamos el modelo para resumir)
        summary = "Resumen: Conversación larga resumida automáticamente."

        # Crear mensaje de resumen
        summary_message = AssistantMessage(
            content=summary, role=MessageRole.assistant, tool_calls=[]
        )

        # Mantener solo mensajes recientes + resumen
        self.messages = recent_messages + [summary_message]
        self._index = {msg.id: msg for msg in self.messages if hasattr(msg, "id")}

        # Guardar cambios
        await self.save()

    async def compact(self) -> None:
        """Compacta la memoria eliminando mensajes antiguos y creando resúmenes."""
        if len(self.messages) > self.summary_threshold:
            await self._create_summary()
