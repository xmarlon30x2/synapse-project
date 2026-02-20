from abc import ABC, abstractmethod

from ..types import Message, ToolCall


class Memory(ABC):
    """
    Interfaz abstracta para la memoria del agente.
    Define los métodos necesarios para almacenar y recuperar mensajes,
    así como para obtener las herramientas pendientes.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Inicializa la memoria"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Cierra la memoria"""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Limpia todos los mensajes"""
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
