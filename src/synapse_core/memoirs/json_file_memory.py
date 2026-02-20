"""
JSONFileMemory - Implementación de Memoria en Archivo JSON

Esta implementación de memoria almacena todos los mensajes del agente en
un archivo JSON local, proporcionando persistencia duradera y capacidad
de recuperación entre sesiones.
"""

import json
from asyncio import to_thread
from dataclasses import asdict
from enum import Enum
from json import JSONEncoder
from pathlib import Path
from typing import Any, cast

from ..mappers import validate_message
from ..types import Message, MessageRole, ToolCall
from .memory import Memory


class _MessageEncoder(JSONEncoder):
    """
    Codificador JSON personalizado para manejar objetos Enum y dataclasses.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, Enum):
            return o.value
        return super().default(o=o)


class JSONFileMemory(Memory):
    """
    Implementación de memoria que guarda los mensajes en un archivo JSON.
    """

    def __init__(self, filename: Path) -> None:
        self.filename: Path = filename
        self.messages: list[Message] = []
        self._index: dict[str, Message] = {}
        self._dirty: bool = False

    async def clear(self) -> None:
        """Limpia todos los mensajes y guarda el estado vacío."""
        self.messages = []
        self._index = {}
        self._dirty = True
        await self._persist()

    async def close(self) -> None:
        """Cierra la memoria guardando cualquier cambio pendiente."""
        if self._dirty:
            await self._persist()

    async def initialize(self) -> None:
        """Carga los mensajes desde el archivo si existe."""
        # Usamos to_thread para no bloquear el event loop con I/O de archivo
        await to_thread(self._load_task)

    def _load_task(self) -> None:
        """Tarea síncrona de carga del archivo."""
        if not self.filename.exists():
            self.messages = []
            self._index = {}
            return

        try:
            with self.filename.open(encoding="utf-8") as file:
                save = json.load(file)
                if not isinstance(save, dict):
                    raise ValueError(
                        "El archivo de memoria debe contener un objeto JSON"
                    )
                save = cast(dict[str, Any], save)
                messages = save.get("messages")
                if not isinstance(messages, list):
                    raise ValueError("Los mensajes deben estar en una lista")
                messages = cast(list[Any], messages)
                self.messages = list(map(validate_message, messages))
                # Crear índice para búsquedas rápidas
                self._index = {
                    msg.id: msg for msg in self.messages if hasattr(msg, "id")
                }
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(
                f"Error cargando memoria desde {self.filename}: {e}"
            ) from e

    async def save(self) -> None:
        """Guarda los mensajes en el archivo JSON de forma asíncrona."""
        self._dirty = True
        await self._persist()

    async def _persist(self) -> None:
        """Método interno para persistir datos de forma asíncrona."""
        if not self._dirty:
            return

        await to_thread(self._save_task)
        self._dirty = False

    def _save_task(self) -> None:
        """Tarea síncrona de guardado."""
        try:
            with self.filename.open(mode="w", encoding="utf-8") as file:
                json.dump(
                    {"messages": list(map(asdict, self.messages))},
                    file,
                    cls=_MessageEncoder,
                    indent=2,
                )
        except Exception as e:
            raise RuntimeError(
                f"Error guardando memoria en {self.filename}: {e}"
            ) from e

    async def all(self) -> list[Message]:
        """Devuelve una copia de la lista de mensajes."""
        return self.messages[:]

    async def add(self, message: Message) -> None:
        """Añade un nuevo mensaje y guarda inmediatamente si es necesario."""
        self.messages.append(message)
        if hasattr(message, "id"):
            self._index[message.id] = message
        # Guardar solo si hay muchos cambios pendientes para optimizar
        if len(self.messages) % 10 == 0:  # Guardar cada 10 mensajes
            await self.save()

    async def next_pending_tool_calls(self) -> list[ToolCall]:
        """
        Identifica las llamadas a herramientas pendientes:
        - Recorre los mensajes.
        - Si encuentra un tool message, marca su call_id como respondido.
        - Si encuentra un assistant message con tool_calls, los considera pendientes
          hasta que aparezca un tool message con ese ID.
        Devuelve la lista de tool calls que aún no tienen respuesta.
        """
        tool_calls: dict[str, ToolCall | None] = {}

        for message in self.messages:
            if message.role == MessageRole.tool:
                # Este ID ya tiene respuesta
                tool_calls[message.call_id] = None

            elif message.role == MessageRole.assistant:
                for tool_call in message.tool_calls:
                    # Si el ID no está en el diccionario (no tiene respuesta aún)
                    if tool_call.id not in tool_calls:
                        tool_calls[tool_call.id] = tool_call
        # Filtramos los que tienen ToolCall (no None) y devolvemos la lista
        return [tool_call for tool_call in tool_calls.values() if tool_call]

    async def get_by_id(self, message_id: str) -> Message | None:
        """Devuelve un mensaje específico por su ID si existe."""
        return self._index.get(message_id)

    async def filter_by_role(self, role: str) -> list[Message]:
        """Devuelve todos los mensajes con un rol específico."""
        return [msg for msg in self.messages if msg.role.value == role]

    async def get_history(self, limit: int = 100) -> list[Message]:
        """Devuelve el historial reciente de mensajes con un límite opcional."""
        return self.messages[-limit:]
