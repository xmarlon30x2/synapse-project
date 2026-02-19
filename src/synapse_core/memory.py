import json
from abc import ABC, abstractmethod
from asyncio import to_thread
from dataclasses import asdict
from enum import Enum
from json import JSONEncoder
from pathlib import Path
from typing import Any, cast

from .mappers import validate_message
from .types import Message, MessageRole, ToolCall


class Memory(ABC):
    """
    Interfaz abstracta para la memoria del agente.
    Define los métodos necesarios para almacenar y recuperar mensajes,
    así como para obtener las herramientas pendientes.
    """

    @abstractmethod
    async def setup(self) -> None:
        """Inicializa la memoria"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Cierra la memoria"""
        pass

    @abstractmethod
    async def all(self) -> list[Message]:
        """Devuelve todos los mensajes almacenados."""
        pass

    @abstractmethod
    async def add(self, message: Message) -> None:
        """Añade un nuevo mensaje a la memoria."""
        pass

    @abstractmethod
    async def next_pending_tool_calls(self) -> list[ToolCall]:
        """
        Devuelve las llamadas a herramientas que aún no tienen respuesta.
        Es decir, tool calls de mensajes assistant que no tienen un tool message correspondiente.
        """
        pass


class MessageEncoder(JSONEncoder):
    """
    Codificador JSON personalizado para manejar objetos Enum.
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

    async def close(self) -> None:
        await self.save()

    async def setup(self) -> None:
        """Carga los mensajes desde el archivo si existe."""
        if not self.filename.exists():
            self.messages = []
            return

        # Usamos to_thread para no bloquear el event loop con I/O de archivo
        await to_thread(self._load_task)

    def _load_task(self) -> None:
        """Tarea síncrona de carga del archivo."""
        with self.filename.open(encoding="utf-8") as file:
            save = json.load(file)
            if not isinstance(save, dict):
                raise ValueError("El archivo de memoria debe contener un objeto JSON")
            save = cast(dict[str, Any], save)
            messages = save.get("messages")
            if not isinstance(messages, list):
                raise ValueError("Los mensajes deben estar en una lista")
            messages = cast(list[Any], messages)
            self.messages = list(map(validate_message, messages))

    async def save(self) -> None:
        """Guarda los mensajes en el archivo JSON."""
        await to_thread(self._save_task)

    def _save_task(self) -> None:
        """Tarea síncrona de guardado."""
        with self.filename.open(mode="w", encoding="utf-8") as file:
            json.dump(
                {"messages": list(map(asdict, self.messages))},
                file,
                cls=MessageEncoder,
            )

    async def all(self) -> list[Message]:
        """Devuelve una copia de la lista de mensajes."""
        return self.messages[:]

    async def add(self, message: Message) -> None:
        """Añade un mensaje y guarda inmediatamente."""
        self.messages.append(message)
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
