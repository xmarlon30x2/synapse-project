from json import load
from typing import Any

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

def validate_message(value: Any):
    if not isinstance(value, dict):
        raise ValueError(
        f"Un mensaje deben ser un dicionario: {value}"
    )
    role = validate_role(value.get("role"))
    match role:
        case MessageRole.user:
            content = validate_content(value.get("content"))
            message = UserMessage(role=role, content=content)
        case MessageRole.assistant:
            content = validate_content(value.get("content"))
            tool_calls = validate_tool_calls(value.get("tool_calls", []))
            message = AssistantMessage(
                role=role, content=content, tool_calls=tool_calls
            )
        case MessageRole.tool:
            content = validate_content(value.get("content"))
            call_id = validate_tool_id(value.get("call_id"))
            message = ToolMessage(role=role, content=content, call_id=call_id)
    return message


def validate_content(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Contenido no valido: {value}")
    return value


def validate_tool_id(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(
            f"ID de herramienta no valido: {value}"
        )
    return value


def validate_tool_call_name(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(
        f"Nombre de la herramienta no valido: {value}"
    )
    return value


def validate_arguments(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(
        f"Argumentos de la herramienta no valido: {value}"
    )
    return value


def validate_role(value: Any) -> MessageRole:
    try:
        return MessageRole(value)
    
    except ValueError:
        raise ValueError(f"Rol no valido: {value}")

def json_filename_to_context_config(json_filename: str):
    with open(json_filename) as file:
        data = load(file)
    return validate_context_config(data)


def validate_context_config(value: Any) -> ContextConfig:
    if not isinstance(value, dict):
        raise ValueError(
        f"La configuracion del contexto deben de ser un dicionario: {value}"
    )
    servers_raw = value.get("servers")
    if not isinstance(servers_raw, list):
        raise ValueError(
        f"Los servers deben de estar en una lista: {servers_raw}"
    )

    return ContextConfig(servers=list(map(validate_server_parameter, servers_raw)))


def validate_server_parameter(value: Any) -> ServerParameters:
    return ServerParameters(**value)  # TODO: Arreglar


def validate_tool_calls(value: Any) -> list[ToolCall]:
    if not isinstance(value, list):
        raise ValueError(
        f"Las llamadas a herramientas deben de ser una lista: {value}"
    )
    return [validate_tool_call(item) for item in value]


def validate_tool_call(value: Any) -> ToolCall:
    if not isinstance(value, dict):
        raise ValueError(
        f"Una llamada a una herramienta deben ser un dicionario: {value}"
    )
    return ToolCall(
        id=validate_tool_id(value.get("id")),
        name=validate_tool_call_name(value.get("name")),
        arguments=validate_arguments(value.get("arguments")),
    )


def server_parameters_to_stdio_server_parameters(
    server_parameters: ServerParameters,
) -> StdioServerParameters:
    return StdioServerParameters(
        args=server_parameters.args,
        command=server_parameters.command,
        cwd=server_parameters.cwd,
        encoding=server_parameters.encoding,
        env=server_parameters.env,
        encoding_error_handler=server_parameters.encoding_error_handler,
    )


def tool_to_tool_definition(tool: Tool) -> ToolDefinition:
    return ToolDefinition(
        name=tool.name,
        description=tool.description or "",
        parameters=tool.inputSchema,
    )


def call_tool_result_to_content(tool_call_result: CallToolResult) -> str:
    parts = []
    if tool_call_result.isError:
        parts.append("Error:")
    for part in tool_call_result.content:
        if isinstance(part, TextContent):
            parts.append(part.text)
        elif isinstance(part, ImageContent):
            parts.append(part.data)
        elif isinstance(part, EmbeddedResource):
            parts.append(
                part.resource.text
                if isinstance(part.resource, TextResourceContents)
                else part.resource.blob
            )
    return "\n".join(parts)


def message_to_message_param(message: Message) -> ChatCompletionMessageParam:
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
    return ChatCompletionMessageToolCallParam(
        id=tool_call.id,
        type="function",
        function=Function(name=tool_call.name, arguments=tool_call.arguments),
    )


def tool_definition_to_tool(tool_definition: ToolDefinition) -> ChatCompletionToolParam:
    return ChatCompletionToolParam(
        type="function",
        function=FunctionDefinition(
            name=tool_definition.name,
            description=tool_definition.description,
            parameters=tool_definition.parameters,
        ),
    )
