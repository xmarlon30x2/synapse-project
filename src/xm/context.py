# context.py
import json
from contextlib import AsyncExitStack
from itertools import chain

from mcp import ClientSession
from mcp.client.stdio import stdio_client

from .mappers import (
    call_tool_result_to_content,
    server_parameters_to_stdio_server_parameters,
    tool_to_tool_definition,
)
from .types import ContextConfig, ToolCall, ToolDefinition, ToolMessage


class Context:
    """Gestiona la conexión con múltiples servidores MCP y la ejecución de herramientas."""

    def __init__(self, config: ContextConfig):
        self.config = config
        self.session_tools_map: dict[ClientSession, list[ToolDefinition]] = {}
        self.stack = AsyncExitStack()

    async def setup(self):
        tools_name = []
        for parameters in self.config.servers:
            stdio_params = server_parameters_to_stdio_server_parameters(parameters)
            read, write = await self.stack.enter_async_context(
                stdio_client(stdio_params)
            )
            session = await self.stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.session_tools_map[session] = []

            result = await session.list_tools()
            for tool_result in result.tools:
                tool_definition = tool_to_tool_definition(tool_result)
                
                if tool_definition.name in tools_name:
                    continue
                
                tools_name.append(tool_definition.name)
                self.session_tools_map[session].append(tool_definition)

    async def call_tool(self, tool_call: ToolCall) -> ToolMessage:
        """Ejecuta una herramienta en el primer servidor que la contenga."""
        for session, tools in self.session_tools_map.items():
            if tool_call.name not in (tool.name for tool in tools):
                continue

            try:
                arguments = json.loads(tool_call.arguments)
            except ValueError as exc:
                return ToolMessage(
                    content=f"Error parseando los parametros de la herramienta '{tool_call.name}': {exc}",
                    call_id=tool_call.id,
                )

            try:
                call_tool_result = await session.call_tool(
                    tool_call.name, arguments=arguments
                )
                content = call_tool_result_to_content(call_tool_result)
                return ToolMessage(
                    content=content,
                    call_id=tool_call.id,
                )

            except Exception as exc:
                return ToolMessage(
                    content=f"Error ejecutando la herramienta '{tool_call.name}': {exc}",
                    call_id=tool_call.id,
                )

        return ToolMessage(
            content=f"Herramienta '{tool_call.name}' no encontrada.",
            call_id=tool_call.id,
        )

    async def close(self) -> None:
        """Cierra todas las sesiones MCP."""
        await self.stack.aclose()
        self.session_tools_map.clear()

    @property
    def tools_definitions(self) -> list[ToolDefinition]:
        return list(
            chain.from_iterable(
                tool_definitions for tool_definitions in self.session_tools_map.values()
            )
        )
