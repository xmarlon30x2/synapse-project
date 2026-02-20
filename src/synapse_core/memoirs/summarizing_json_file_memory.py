from pathlib import Path
from typing import TYPE_CHECKING

from ..types import Message, TextToken, UserMessage
from .json_file_memory import JSONFileMemory

if TYPE_CHECKING:
    from ..model import Model


class SummarizingJSONFileMemory(JSONFileMemory):
    def __init__(
        self,
        filename: Path,
        max_messages: int,
        sumarize_message: int,
        sumarize_prompt: str,
        model: "Model",
    ) -> None:
        super().__init__(filename=filename)
        self.max_messages: int = max_messages
        self.sumarize_message: int = sumarize_message
        self.sumarize_prompt: str = sumarize_prompt
        self.model = model

    async def add(self, message: Message) -> None:
        self.messages.append(message)
        await self.sumarize_chat()
        await self.save()

    async def sumarize_chat(self) -> None:
        if len(self.messages) < self.max_messages:
            return

        self.messages, overflow_messages = (
            self.messages[self.sumarize_message:],
            self.messages[:self.sumarize_message],
        )
        overflow_messages.append(UserMessage(content=self.sumarize_prompt))

        summary = "Resumen de la converzacion:\n"
        async for token in self.model.create_chat_stream(
            messages=overflow_messages, tool_definitions=[]
        ):
            if isinstance(token, TextToken):
                summary += token.text

        self.messages.insert(0, UserMessage(content=summary))

    async def initialize(self) -> None:
        await super().initialize()
        await self.sumarize_chat()
        await self.save()
