"""
Proyecto Synapse - Sistema de Agentes Inteligentes

Synapse es un framework para crear agentes conversacionales con soporte para
herramientas externas y memoria persistente. Utiliza el protocolo MCP
(Model Context Protocol) para interactuar con múltiples servidores de herramientas.

Módulos principales:
- core: Componentes fundamentales del sistema
- agents: Clases de agentes y su ciclo de vida
- protocols: Implementaciones de protocolos (MCP, etc.)
- storage: Sistemas de persistencia y memoria
- types: Definiciones de tipos y modelos de datos
"""

from .agent import Agent
from .context import Context
from .memoirs.json_file_memory import JSONFileMemory
from .memoirs.memory import Memory
from .model import Model
from .types import (
    AssistantMessage,
    ChatIDToken,
    ContextConfig,
    Message,
    MessageRole,
    ServerParameters,
    TextToken,
    TokenType,
    ToolCall,
    ToolCallArgumentsToken,
    ToolCallIDToken,
    ToolCallNameToken,
    ToolDefinition,
    ToolMessage,
    UserMessage,
)

__all__ = [
    # Tipos
    "Message",
    "MessageRole",
    "AssistantMessage",
    "UserMessage",
    "ToolMessage",
    "ToolCall",
    "ToolDefinition",
    "ServerParameters",
    "ContextConfig",
    "TokenType",
    "TextToken",
    "ToolCallNameToken",
    "ToolCallIDToken",
    "ToolCallArgumentsToken",
    "ChatIDToken",
    # Clases principales
    "Agent",
    "Context",
    "Model",
    "Memory",
    "JSONFileMemory",
]

__version__ = "1.0.1"
__author__ = "Synapse Project"
__description__ = "Framework de agentes conversacionales con soporte MCP"
