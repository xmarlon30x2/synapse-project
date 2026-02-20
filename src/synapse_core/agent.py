"""
Agente Principal - Coordinador del Sistema

Este módulo implementa el agente principal que coordina el modelo de lenguaje,
la memoria persistente y el contexto de ejecución de herramientas externas.
"""

from collections import defaultdict
from collections.abc import AsyncGenerator
from typing import Any

from .context import Context
from .memoirs.memory import Memory
from .model import Model
from .types import (
    AssistantMessage,
    Message,
    Token,
    TokenType,
    ToolCall,
    ToolMessage,
)


class Agent:
    """
    Agente principal que coordina el modelo, la memoria y el contexto.
    Ejecuta un ciclo de vida donde el modelo genera respuestas y el contexto ejecuta herramientas.
    """

    def __init__(self, model: Model, memory: Memory, context: Context) -> None:
        # Guardamos el modelo
        self.model: Model = model

        # Guardamos la memoria
        self.memory: Memory = memory

        # Guardamos el contexto
        self.context: Context = context

    async def __aenter__(self):
        await self.memory.initialize()
        await self.context.setup()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.context.close()
        await self.memory.close()

    async def next_stream(self) -> AsyncGenerator[Message | Token, Any]:
        """
        Ejecuta el ciclo de vida del agente y devuelve un generador asíncrono
        que produce tokens y mensajes a medida que se generan.
        """
        # Primero buscamos herramientas pendientes en la memoria
        # (llamadas a herramientas que aún no tienen respuesta)
        pending_tool_calls: (
            list[ToolCall] | None
        ) = await self.memory.next_pending_tool_calls()

        # No ejecutar el modelo si hay tareas pendientes (porque primero hay que procesar las respuestas)
        # Inicialmente, si no hay herramientas pendientes, el modelo está "sucio" (debe ejecutarse)
        model_dirty: bool = not pending_tool_calls

        # Marcar como sucio dependiendo si hay herramientas pendientes
        # Si hay herramientas pendientes, el contexto debe ejecutarlas
        context_dirty = bool(pending_tool_calls)

        # Continuamos el ciclo si el modelo o el contexto esta sucio
        # Lo que queremos es que la primera vez siempre inicie
        # ya sea porque hay herramientas pendientes o porque sino se
        # marcara como sucio el modelo
        while model_dirty or context_dirty:
            # Si el modelo esta sucio ejecutar el modelo
            if model_dirty:
                # Obtenemos todos los mensajes de la memoria
                messages: list[Message] = await self.memory.all()

                # Creamos un buffer para el contenido del texto
                content_buffer: str = ""

                # Creamos un buffer para las llamadas a herramientas
                # Es un diccionario con las claves como índices y los valores como llamadas a herramientas
                # para poder acceder a cualquier llamada a herramienta sin importar el orden en el
                # que llegue el token (porque pueden venir fragmentadas en varios chunks)
                tool_calls_buffer: dict[int, ToolCall] = defaultdict(
                    lambda: ToolCall(id="", name="", arguments="")
                )

                # Creamos un chat en streaming con el modelo
                async for token in self.model.create_chat_stream(
                    # Le pasamos los mensajes
                    messages=messages,
                    # Y le pasamos las definiciones de las herramientas disponibles
                    # en el contexto
                    tool_definitions=self.context.tools_definitions,
                ):
                    # Si el token es un texto
                    if token.type == TokenType.text:
                        # Guardamos el texto en el buffer de texto
                        content_buffer += token.text

                    # Si el token es un ID de una llamada a una herramienta
                    elif token.type == TokenType.tool_call_id:
                        # Guardamos el ID en la llamada a herramienta dependiendo del índice
                        # Si el índice no existe no importa porque tool_calls_buffer es un defaultdict
                        # y creará la llamada a herramienta sola
                        tool_calls_buffer[token.index].id += token.id

                    # Si el token es un nombre de una llamada a una herramienta
                    elif token.type == TokenType.tool_call_name:
                        # Guardamos el nombre en la llamada a herramienta dependiendo del índice
                        # igual que en el anterior tipo de token
                        tool_calls_buffer[token.index].name += token.name

                    # Si el token es un argumento de una llamada a una herramienta
                    elif token.type == TokenType.tool_call_arguments:
                        # Guardamos el argumento en la llamada a herramienta dependiendo del índice
                        # igual que en el anterior tipo de token
                        tool_calls_buffer[token.index].arguments += token.arguments

                    # Devolvemos el token al cliente
                    yield token

                # Si se generó texto o llamada a herramientas
                if content_buffer or tool_calls_buffer:
                    # Ordenar las llamadas a herramientas por índice
                    tool_calls: list[ToolCall] = [
                        tool_call
                        for _, tool_call in sorted(
                            tool_calls_buffer.items(), key=lambda item: item[0]
                        )
                    ]

                    # Crear el mensaje del asistente
                    assistant_message = AssistantMessage(
                        content=content_buffer, tool_calls=tool_calls
                    )

                    # Guardar el mensaje del asistente en la memoria
                    await self.memory.add(message=assistant_message)

                    # Devolver el mensaje completo (útil para quien necesite el mensaje ya armado)
                    yield assistant_message

                # Limpiar el modelo: ya no está sucio porque acabamos de ejecutarlo
                model_dirty = False
                # Si se usaron herramientas (tool_calls no vacío), marcar como sucio al contexto
                # para que en la siguiente iteración las ejecute.
                # De no haberse usado herramientas, el ciclo terminaría
                # ya que todo está limpio (model_dirty=False, context_dirty=False)
                context_dirty = bool(tool_calls_buffer)

            # Si el contexto esta sucio ejecutar el contexto
            if context_dirty:
                # Usamos las herramientas pendientes creadas al inicio del ciclo
                # o buscamos de nuevo en caso de que no las tengamos ya
                pending_tool_calls = (
                    pending_tool_calls or await self.memory.next_pending_tool_calls()
                )

                # Iteramos sobre todas las herramientas pendientes
                for tool_call in pending_tool_calls:
                    # Ejecutamos la herramienta a través del contexto
                    tool_message: ToolMessage = await self.context.call_tool(
                        tool_call=tool_call
                    )

                    # Guardamos el resultado (mensaje de herramienta) en la memoria
                    await self.memory.add(message=tool_message)

                    # Devolvemos el resultado al cliente
                    yield tool_message

                # Si había herramientas pendientes, marcamos el modelo como
                # sucio ya que tiene que procesar las respuestas de esas herramientas
                model_dirty = bool(pending_tool_calls)

                # Después de esto no quedarán herramientas pendientes
                # entonces limpiamos el contexto
                context_dirty = False
                # Borramos las herramientas pendientes actuales para
                # que en el próximo ciclo use las nuevas (si las hay)
                pending_tool_calls = None
