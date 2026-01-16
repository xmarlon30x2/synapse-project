import json
from contextlib import AsyncExitStack
from itertools import chain

from mcp import ClientSession, ListToolsResult, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

from .mappers import (
    call_tool_result_to_content,
    server_parameters_to_stdio_server_parameters,
    tool_to_tool_definition,
)
from .types import ContextConfig, ToolCall, ToolDefinition, ToolMessage


class Context:
    """
    Gestiona la conexión con múltiples servidores MCP (Model Context Protocol)
    y la ejecución de herramientas.
    """

    def __init__(self, config: ContextConfig) -> None:
        self.config: ContextConfig = config
        # Mapa que asocia cada sesión de cliente con la lista de definiciones de herramientas que ofrece
        self.session_tools_map: dict[ClientSession, list[ToolDefinition]] = {}
        # Pila asíncrona para gestionar la entrada y salida de contextos (cliente stdio, sesiones)
        self.stack: AsyncExitStack[bool | None] = AsyncExitStack()

    async def setup(self) -> None:
        """
        Inicializa las conexiones con los servidores MCP definidos en la configuración.
        Para cada servidor, establece un cliente stdio, crea una sesión y obtiene la lista de herramientas.
        """
        tools_name: list[
            str
        ] = []  # Lista temporal para evitar duplicados de nombres de herramientas entre servidores
        for parameters in self.config.servers:
            # Convierte los parámetros del servidor a formato StdioServerParameters de MCP
            stdio_params: StdioServerParameters = (
                server_parameters_to_stdio_server_parameters(
                    server_parameters=parameters
                )
            )
            # Establece la comunicación stdio con el servidor
            read, write = await self.stack.enter_async_context(
                cm=stdio_client(server=stdio_params)
            )
            # Crea una sesión MCP sobre esa comunicación
            session: ClientSession = await self.stack.enter_async_context(
                cm=ClientSession(read_stream=read, write_stream=write)
            )
            await session.initialize()
            self.session_tools_map[session] = []

            # Solicita la lista de herramientas disponibles en el servidor
            result: ListToolsResult = await session.list_tools()
            for tool_result in result.tools:
                # Convierte la herramienta MCP a nuestra definición interna
                tool_definition: ToolDefinition = tool_to_tool_definition(
                    tool=tool_result
                )

                # Evita registrar herramientas con el mismo nombre (primera que aparece)
                if tool_definition.name in tools_name:
                    continue

                tools_name.append(tool_definition.name)
                self.session_tools_map[session].append(tool_definition)

    async def call_tool(self, tool_call: ToolCall) -> ToolMessage:
        """
        Ejecuta una herramienta en el primer servidor que la contenga.
        Si falla la ejecución, devuelve un mensaje de error.
        """
        # Recorremos todas las sesiones y sus herramientas
        for session, tools in self.session_tools_map.items():
            # Si la herramienta no está en esta sesión, pasamos a la siguiente
            if tool_call.name not in (tool.name for tool in tools):
                continue

            # Intentamos parsear los argumentos (vienen como string JSON)
            try:
                arguments = json.loads(tool_call.arguments)
            except ValueError as exc:
                return ToolMessage(
                    content=f"Error parseando los parámetros de la herramienta '{tool_call.name}': {exc}",
                    call_id=tool_call.id,
                )

            # Ejecutamos la herramienta en la sesión
            try:
                call_tool_result: CallToolResult = await session.call_tool(
                    name=tool_call.name, arguments=arguments
                )
                # Convertimos el resultado a texto plano
                content: str = call_tool_result_to_content(
                    tool_call_result=call_tool_result
                )
                return ToolMessage(
                    content=content,
                    call_id=tool_call.id,
                )
            except Exception as exc:
                return ToolMessage(
                    content=f"Error ejecutando la herramienta '{tool_call.name}': {exc}",
                    call_id=tool_call.id,
                )

        # Si ninguna sesión contiene la herramienta
        return ToolMessage(
            content=f"Herramienta '{tool_call.name}' no encontrada.",
            call_id=tool_call.id,
        )

    async def close(self) -> None:
        """Cierra todas las sesiones MCP y limpia el mapa."""
        await self.stack.aclose()
        self.session_tools_map.clear()

    @property
    def tools_definitions(self) -> list[ToolDefinition]:
        """
        Devuelve una lista plana con todas las definiciones de herramientas
        de todos los servidores.
        """
        return list(
            chain.from_iterable(
                tool_definitions
                for tool_definitions in self.session_tools_map.values()
            )
        )
