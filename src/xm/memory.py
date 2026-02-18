from abc import ABC, abstractmethod
from json import dump, load, JSONEncoder
from pathlib import Path
from asyncio import to_thread
from dataclasses import asdict

from .mappers import validate_message
from .types import Message, MessageRole, ToolCall


class Memory(ABC):
    @abstractmethod
    async def setup(self) -> None:
        pass

    @abstractmethod
    async def all(self) -> list[Message]:
        pass

    @abstractmethod
    async def add(self, message: Message) -> None:
        pass

    @abstractmethod
    async def next_pending_tool_calls(self) -> list[ToolCall]:
        pass


class MessageEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)


class JSONFileMemory(Memory):
    def __init__(self, filename: Path) -> None:
        self.filename = filename
        self.messages = []

    async def setup(self):
        if not self.filename.exists():
            self.messages = []
            return
        
        await to_thread(self._load_task)
    
    def _load_task(self):
        with open(self.filename) as file:
            save = load(file)
            if not isinstance(save, dict):
                raise ValueError(
                "El archivo de memoria debe contener un json"
            )
            messages = save.get("messages")
            if not isinstance(messages, list):
                raise ValueError(
                "Los menajes deben ser estar en una lista"
            )
            self.messages = list(map(validate_message, messages))

    async def save(self):
        await to_thread(self._save_task)
    
    def _save_task(self):
        with open(self.filename, "w", encoding='utf-8') as file:
            dump({"messages": list(map(asdict, self.messages))}, file, cls=MessageEncoder)

    async def all(self) -> list[Message]:
        return self.messages[:]

    async def add(self, message: Message) -> None:
        self.messages.append(message)
        await self.save()

    async def next_pending_tool_calls(self) -> list[ToolCall]:
        tool_calls: dict[str, ToolCall | None] = {}

        for message in self.messages:
            if message.role == MessageRole.tool:
                tool_calls[message.call_id] = None

            elif message.role == MessageRole.assistant:
                for tool_call in message.tool_calls:
                    if tool_call.id not in tool_calls:
                        tool_calls[tool_call.id] = tool_call
        return [tool_call for tool_call in tool_calls.values() if tool_call]
