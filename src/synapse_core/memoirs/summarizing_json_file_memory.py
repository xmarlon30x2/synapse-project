"""
SummarizingJSONFileMemory - Implementación de Memoria con Resumen

Esta implementación extiende JSONFileMemory añadiendo funcionalidad de resumen
de conversaciones largas para mantener la memoria eficiente y enfocada.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from ..types import Message, TextToken, UserMessage
from .json_file_memory import JSONFileMemory

if TYPE_CHECKING:
    from ..model import Model


class SummarizingJSONFileMemory(JSONFileMemory):
    """
    Implementación de memoria que guarda los mensajes en un archivo JSON
    con capacidad de resumir conversaciones largas.
    """

    def __init__(
        self,
        filename: Path,
        model: 'Model',
        sumarize_prompt: str,
        max_messages: int = 100,
        summary_threshold: int = 50,
    ) -> None:
        super().__init__(filename)
        self.model = model
        self.max_messages: int = max_messages
        self.summary_threshold: int = summary_threshold
        self.sumarize_prompt: str = sumarize_prompt

    async def add(self, message: Message) -> None:
        """Añade un nuevo mensaje y gestiona el resumen si es necesario."""
        await super().add(message)

        # Comprobar si necesitamos resumir
        if len(self.messages) > self.summary_threshold:
            await self._create_summary()

    async def _create_summary(self) -> None:
        """Crea un resumen de la conversación y mantiene solo los mensajes recientes."""
        self.messages, overflow_messages = (
            self.messages[self.summary_threshold :],
            self.messages[: self.summary_threshold],
        )
        overflow_messages.append(UserMessage(content=self.sumarize_prompt))

        summary = "Resumen de la converzacion:\n"
        async for token in self.model.create_chat_stream(
            messages=overflow_messages, tool_definitions=[]
        ):
            if isinstance(token, TextToken):
                summary += token.text

        self.messages.insert(0, UserMessage(content=summary))
        await self.save()

    async def compact(self) -> None:
        """Compacta la memoria eliminando mensajes antiguos y creando resúmenes."""
        if len(self.messages) > self.max_messages:
            await self._create_summary()
