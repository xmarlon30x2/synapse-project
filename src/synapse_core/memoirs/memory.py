"""
Memoria - Interfaz Abstracta para Persistencia

Este módulo define la interfaz abstracta para implementaciones de memoria
que permiten almacenar y recuperar el historial de conversaciones del agente.
"""

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
        """Inicializa la memoria."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Cierra la memoria y libera recursos."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Limpia todos los mensajes almacenados."""
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

    @abstractmethod
    async def get_by_id(self, message_id: str) -> Message | None:
        """
        Devuelve un mensaje específico por su ID si existe.
        """
        pass

    @abstractmethod
    async def filter_by_role(self, role: str) -> list[Message]:
        """
        Devuelve todos los mensajes con un rol específico.
        """
        pass

    @abstractmethod
    async def get_history(self, limit: int = 100) -> list[Message]:
        """
        Devuelve el historial reciente de mensajes con un límite opcional.
        """
        pass
