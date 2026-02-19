import json
from os.path import exists
from typing import Any, cast

from mcp import StdioServerParameters, Tool
from mcp.types import (
    CallToolResult,
    EmbeddedResource,
    ImageContent,
    TextContent,
    TextResourceContents,
)
from openai.types.chat.chat_completion_assistant_message_param import (
    ChatCompletionAssistantMessageParam,
)
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message_tool_call_param import (
    ChatCompletionMessageToolCallParam,
    Function,
)
from openai.types.chat.chat_completion_tool_message_param import (
    ChatCompletionToolMessageParam,
)
from openai.types.chat.chat_completion_tool_param import ChatCompletionToolParam
from openai.types.chat.chat_completion_user_message_param import (
    ChatCompletionUserMessageParam,
)
from openai.types.shared_params.function_definition import FunctionDefinition

from .types import (
    AssistantMessage,
    ContextConfig,
    Message,
    MessageRole,
    ServerParameters,
    ToolCall,
    ToolDefinition,
    ToolMessage,
    UserMessage,
)

# Funciones de validación y conversión entre nuestros tipos internos y los tipos de OpenAI/MCP


def validate_message(value: Any) -> Message:
    """
    Valida que un diccionario crudo (por ejemplo, desde JSON) sea un mensaje válido
    y devuelve la instancia de Message correspondiente (UserMessage, AssistantMessage o ToolMessage).
    """
    if not isinstance(value, dict):
        raise ValueError(f"Un mensaje debe ser un diccionario: {value}")
    value = cast(dict[str, Any], value)
    role: MessageRole = validate_role(value=value.get("role"))
    match role:
        case MessageRole.user:
            content: str = validate_content(value=value.get("content"))
            message = UserMessage(role=role, content=content)
        case MessageRole.assistant:
            content = validate_content(value=value.get("content"))
            tool_calls: list[ToolCall] = validate_tool_calls(
                value.get("tool_calls", [])
            )
            message = AssistantMessage(
                role=role, content=content, tool_calls=tool_calls
            )
        case MessageRole.tool:
            content = validate_content(value=value.get("content"))
            call_id: str = validate_tool_id(value=value.get("call_id"))
            message = ToolMessage(role=role, content=content, call_id=call_id)
    return message


def validate_content(value: Any) -> str:
    """Valida que el contenido sea un string."""
    if not isinstance(value, str):
        raise ValueError(f"Contenido no válido: {value}")
    return value


def validate_tool_id(value: Any) -> str:
    """Valida que el ID de herramienta sea un string."""
    if not isinstance(value, str):
        raise ValueError(f"ID de herramienta no válido: {value}")
    return value


def validate_tool_call_name(value: Any) -> str:
    """Valida que el nombre de la herramienta sea un string."""
    if not isinstance(value, str):
        raise ValueError(f"Nombre de la herramienta no válido: {value}")
    return value


def validate_arguments(value: Any) -> str:
    """Valida que los argumentos de la herramienta sean un string JSON."""
    if not isinstance(value, str):
        raise ValueError(f"Argumentos de la herramienta no válidos: {value}")
    return value


def validate_role(value: Any) -> MessageRole:
    """Valida que el rol sea uno de los permitidos y devuelve el enum."""
    try:
        return MessageRole(value=value)
    except ValueError:
        raise ValueError(f"Rol no válido: {value}") from None


def json_filename_to_context_config(json_filename: str) -> ContextConfig:
    """Lee un archivo JSON y lo convierte en un objeto ContextConfig."""
    if exists(path=json_filename):
        with open(file=json_filename, encoding='utf-8') as file:
            data: Any = json.load(file)
        return validate_context_config(value=data)
    return ContextConfig(servers=[])


def validate_context_config(value: Any) -> ContextConfig:
    """Valida que el diccionario de configuración del contexto sea correcto."""
    if not isinstance(value, dict):
        raise ValueError(
            f"La configuración del contexto debe ser un diccionario: {value}"
        )
    value = cast(dict[str, Any], value)
    servers_raw = value.get("servers")
    if not isinstance(servers_raw, list):
        raise ValueError(f"Los servidores deben estar en una lista: {servers_raw}")
    servers_raw = cast(list[Any], servers_raw)
    return ContextConfig(servers=list(map(validate_server_parameter, servers_raw)))


def validate_server_parameter(value: Any) -> ServerParameters:
    """Convierte un diccionario en un objeto ServerParameters (validación básica)."""
    # TODO: Mejorar validación (campos requeridos, tipos, etc.)
    return ServerParameters(**value)


def validate_tool_calls(value: Any) -> list[ToolCall]:
    """Valida que sea una lista de llamadas a herramientas."""
    if not isinstance(value, list):
        raise ValueError(f"Las llamadas a herramientas deben ser una lista: {value}")
    value = cast(list[Any], value)
    return [validate_tool_call(value=item) for item in value]


def validate_tool_call(value: Any) -> ToolCall:
    """Valida un diccionario de llamada a herramienta y devuelve un objeto ToolCall."""
    if not isinstance(value, dict):
        raise ValueError(
            f"Una llamada a una herramienta debe ser un diccionario: {value}"
        )
    value = cast(dict[str, Any], value)
    return ToolCall(
        id=validate_tool_id(value=value.get("id")),
        name=validate_tool_call_name(value=value.get("name")),
        arguments=validate_arguments(value=value.get("arguments")),
    )


def server_parameters_to_stdio_server_parameters(
    server_parameters: ServerParameters,
) -> StdioServerParameters:
    """Convierte nuestros ServerParameters a los parámetros que espera MCP para stdio."""
    return StdioServerParameters(
        args=server_parameters.args,
        command=server_parameters.command,
        cwd=server_parameters.cwd,
        encoding=server_parameters.encoding,
        env=server_parameters.env,
        encoding_error_handler=server_parameters.encoding_error_handler,
    )


def tool_to_tool_definition(tool: Tool) -> ToolDefinition:
    """Convierte una herramienta de MCP a nuestra definición interna."""
    return ToolDefinition(
        name=tool.name,
        description=tool.description or "",
        parameters=tool.inputSchema,
    )


def call_tool_result_to_content(tool_call_result: CallToolResult) -> str:
    """
    Convierte el resultado de una llamada a herramienta (que puede contener múltiples partes)
    en un solo string de texto plano.
    """
    parts: list[str] = []
    if tool_call_result.isError:
        parts.append("Error:")
    for part in tool_call_result.content:
        if isinstance(part, TextContent):
            parts.append(part.text)
        elif isinstance(part, ImageContent):
            # En este caso, convertimos la imagen a su representación base64
            parts.append(part.data)
        elif isinstance(part, EmbeddedResource):
            # Si es un recurso de texto, extraemos el texto; si es binario, extraemos el blob
            parts.append(
                part.resource.text
                if isinstance(part.resource, TextResourceContents)
                else part.resource.blob
            )
    return "\n".join(parts)


def message_to_message_param(message: Message) -> ChatCompletionMessageParam:
    """Convierte un mensaje interno al formato que espera la API de OpenAI."""
    if message.role is MessageRole.user:
        return ChatCompletionUserMessageParam(content=message.content, role="user")

    if message.role is MessageRole.assistant:
        return ChatCompletionAssistantMessageParam(
            role="assistant",
            content=message.content if message.content else None,
            tool_calls=list(map(tool_call_to_tool_call_param, message.tool_calls)),
        )

    if message.role is MessageRole.tool:
        return ChatCompletionToolMessageParam(
            role="tool", content=message.content, tool_call_id=message.call_id
        )

    raise NotImplementedError(f"Rol no implementado: {message.role}")


def tool_call_to_tool_call_param(
    tool_call: ToolCall,
) -> ChatCompletionMessageToolCallParam:
    """Convierte una llamada a herramienta interna al formato de OpenAI."""
    return ChatCompletionMessageToolCallParam(
        id=tool_call.id,
        type="function",
        function=Function(name=tool_call.name, arguments=tool_call.arguments),
    )


def tool_definition_to_tool(
    tool_definition: ToolDefinition,
) -> ChatCompletionToolParam:
    """Convierte una definición de herramienta interna al formato que OpenAI espera en la solicitud."""
    return ChatCompletionToolParam(
        type="function",
        function=FunctionDefinition(
            name=tool_definition.name,
            description=tool_definition.description,
            parameters=tool_definition.parameters,
        ),
    )
