from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class MessageRole(Enum):
    """Roles posibles de los mensajes en la conversación."""

    user = "user"
    assistant = "assistant"
    tool = "tool"


@dataclass
class ToolCall:
    """Representa una llamada a una herramienta generada por el asistente."""

    id: str
    name: str
    arguments: str  # string JSON con los argumentos


@dataclass
class ToolDefinition:
    """Definición de una herramienta disponible (nombre, descripción, esquema de parámetros)."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class UserMessage:
    """Mensaje enviado por el usuario."""

    content: str
    role: Literal[MessageRole.user] = MessageRole.user


@dataclass
class AssistantMessage:
    """Mensaje generado por el asistente, puede incluir llamadas a herramientas."""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)  # type: ignore
    role: Literal[MessageRole.assistant] = MessageRole.assistant


@dataclass
class ToolMessage:
    """Resultado de la ejecución de una herramienta."""

    content: str
    call_id: str  # ID de la llamada a herramienta a la que responde
    role: Literal[MessageRole.tool] = MessageRole.tool


# Tipo unión para cualquier mensaje
type Message = ToolMessage | AssistantMessage | UserMessage


@dataclass
class ServerParameters:
    """Parámetros para configurar un servidor MCP vía stdio."""

    command: str
    args: list[str] = field(default_factory=list)  # type: ignore
    env: dict[str, str] | None = None
    cwd: str | None = None
    encoding: str = "utf-8"
    encoding_error_handler: Literal["strict", "ignore", "replace"] = "strict"


@dataclass
class ContextConfig:
    """Configuración completa del contexto: lista de servidores."""

    servers: list[ServerParameters]


class TokenType(Enum):
    """Tipos de tokens que puede emitir el stream del modelo."""

    text = "text"
    tool_call_name = "tool_call_name"
    tool_call_id = "tool_call_id"
    tool_call_arguments = "tool_call_arguments"
    chat_id = "chat_id"


@dataclass
class TextToken:
    """Token de texto plano."""

    text: str
    type: Literal[TokenType.text] = TokenType.text


@dataclass
class ToolCallNameToken:
    """Token con parte del nombre de una herramienta (puede venir fragmentado)."""

    index: int
    name: str
    type: Literal[TokenType.tool_call_name] = TokenType.tool_call_name


@dataclass
class ToolCallIDToken:
    """Token con el ID de una llamada a herramienta."""

    index: int
    id: str
    type: Literal[TokenType.tool_call_id] = TokenType.tool_call_id


@dataclass
class ToolCallArgumentsToken:
    """Token con parte de los argumentos JSON de una herramienta."""

    index: int
    arguments: str
    type: Literal[TokenType.tool_call_arguments] = TokenType.tool_call_arguments


@dataclass
class ChatIDToken:
    """Token que contiene el ID de la conversación (suele ser el primero)."""

    id: str
    type: Literal[TokenType.chat_id] = TokenType.chat_id


# Tipo unión para cualquier token
type Token = (
    TextToken
    | ToolCallArgumentsToken
    | ToolCallIDToken
    | ToolCallNameToken
    | ChatIDToken
)
