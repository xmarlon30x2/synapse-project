"""
Modelo de Lenguaje - Integración con OpenAI

Este módulo encapsula la conexión con modelos de lenguaje a través de la API
de OpenAI-compatible y proporciona un flujo de tokens para procesamiento
de streaming.
"""

from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat.chat_completion_chunk import (
    ChoiceDelta,
    ChoiceDeltaToolCallFunction,
)
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam

from .mappers import message_to_message_param, tool_definition_to_tool
from .types import (
    ChatIDToken,
    Message,
    TextToken,
    Token,
    ToolCallArgumentsToken,
    ToolCallIDToken,
    ToolCallNameToken,
    ToolDefinition,
)


class Model:
    """
    Encapsula un modelo de lenguaje (a través de la API de OpenAI-compatible)
    y proporciona un método para crear un chat en streaming.
    """

    def __init__(
        self, api_key: str, base_url: str, model: str, temperature: float = 1
    ) -> None:
        # Cliente asíncrono de OpenAI
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model: str = model
        self.temperature: float = temperature

    async def create_chat_stream(
        self,
        messages: list[Message],
        tool_definitions: list[ToolDefinition],
        store: bool | None = None,
        chat_id: str | None = None,
    ) -> AsyncGenerator[Token, Any]:
        """
        Envía una solicitud de chat en streaming al modelo.
        Convierte los mensajes internos y las definiciones de herramientas al formato de OpenAI,
        y luego itera sobre los chunks de la respuesta, generando tokens de nuestro tipo.
        """
        # Convertir mensajes internos a parámetros de OpenAI
        message_params: list[ChatCompletionMessageParam] = list(
            map(message_to_message_param, messages)
        )
        # Convertir definiciones de herramientas al formato de OpenAI
        tools: list[ChatCompletionToolParam] = list(
            map(tool_definition_to_tool, tool_definitions)
        )
        id_emited = False  # Control para emitir el ID del chat solo una vez

        # Llamada a la API con streaming
        async for chunk in await self.client.chat.completions.create(
            messages=message_params,
            model=self.model,
            tools=tools,
            tool_choice="auto",
            temperature=self.temperature,
            stream=True,
            parallel_tool_calls=True,
            store=store,
        ):
            # Emitimos el ID del chat solo una vez, si no se proporcionó externamente
            if not id_emited and not chat_id:
                id_emited = True
                yield ChatIDToken(id=chunk.id)

            delta: ChoiceDelta = chunk.choices[0].delta

            # Si hay contenido de texto
            if delta.content is not None:
                yield TextToken(text=delta.content)

            # Si hay llamadas a herramientas en este chunk
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    # ID de la herramienta (puede venir en un chunk separado)
                    if tool_call.id:
                        yield ToolCallIDToken(id=tool_call.id, index=tool_call.index)

                    if not tool_call.function:
                        continue

                    function: ChoiceDeltaToolCallFunction = tool_call.function

                    # Nombre de la herramienta
                    if function.name:
                        yield ToolCallNameToken(
                            name=function.name, index=tool_call.index
                        )

                    # Argumentos (pueden venir fragmentados)
                    if function.arguments:
                        yield ToolCallArgumentsToken(
                            arguments=function.arguments,
                            index=tool_call.index,
                        )
