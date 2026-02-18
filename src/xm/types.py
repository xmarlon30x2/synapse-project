# types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    tool = "tool"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass
class UserMessage:
    content: str

    role: Literal[MessageRole.user] = MessageRole.user


@dataclass
class AssistantMessage:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)

    role: Literal[MessageRole.assistant] = MessageRole.assistant


@dataclass
class ToolMessage:
    content: str
    call_id: str

    role: Literal[MessageRole.tool] = MessageRole.tool


type Message = ToolMessage | AssistantMessage | UserMessage


@dataclass
class ServerParameters:
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    cwd: str | None = None
    encoding: str = "utf-8"
    encoding_error_handler: Literal["strict", "ignore", "replace"] = "strict"


@dataclass
class ContextConfig:
    servers: list[ServerParameters]


class TokenType(str, Enum):
    text = "text"
    tool_call_name = "tool_call_name"
    tool_call_id = "tool_call_id"
    tool_call_arguments = "tool_call_arguments"
    chat_id = "chat_id"


@dataclass
class TextToken:
    text: str
    type: Literal[TokenType.text] = TokenType.text


@dataclass
class ToolCallNameToken:
    index: int
    name: str
    type: Literal[TokenType.tool_call_name] = TokenType.tool_call_name


@dataclass
class ToolCallIDToken:
    index: int
    id: str
    type: Literal[TokenType.tool_call_id] = TokenType.tool_call_id


@dataclass
class ToolCallArgumentsToken:
    index: int
    arguments: str
    type: Literal[TokenType.tool_call_arguments] = TokenType.tool_call_arguments


@dataclass
class ChatIDToken:
    id: str
    type: Literal[TokenType.chat_id] = TokenType.chat_id


type Token = (
    TextToken
    | ToolCallArgumentsToken
    | ToolCallIDToken
    | ToolCallNameToken
    | ChatIDToken
)
