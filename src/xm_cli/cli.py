from asyncio import to_thread
from collections.abc import Callable
from types import CoroutineType
from typing import Any

from xm.agent import Agent
from xm.types import (
    TextToken,
    ToolCallArgumentsToken,
    ToolCallIDToken,
    ToolCallNameToken,
    ToolMessage,
    UserMessage,
)


class XMCli:
    def __init__(self, agent: Agent):
        self.agent = agent
        self.prompt = "user> "
        self.command_registry: dict[
            str, Callable[[str], CoroutineType[Any, Any, None]]
        ] = {"exit": self.exit, "write": self.write}

    async def exit(self, arg: str):
        raise KeyboardInterrupt()

    async def write(self, arg: str):
        user_message = UserMessage(content=arg)
        await self.agent.memory.add(user_message)

    async def next(self, user_input: str):
        await self.write(user_input)

        async for chunk in self.agent.next_stream():
            if isinstance(chunk, TextToken):
                await to_thread(print, chunk.text, flush=True, end="")

            elif isinstance(chunk, ToolCallIDToken):
                await to_thread(print, f"\n(call:{chunk.id})", flush=True, end="")

            elif isinstance(chunk, ToolCallNameToken):
                await to_thread(print, f" {chunk.name}> ", flush=True, end="")

            elif isinstance(chunk, ToolCallArgumentsToken):
                await to_thread(print, chunk.arguments, flush=True, end="")

            elif isinstance(chunk, ToolMessage):
                await to_thread(
                    print, f"\n(tool:{chunk.call_id})", chunk.content, flush=True
                )

        await to_thread(print, "\n")

    async def loop(self):
        try:
            while True:
                user_input = await to_thread(input, self.prompt)

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    cmd, *args = user_input[1:].strip().split(maxsplit=1)
                    args = args[0] if args else ""
                    command_handler = self.command_registry.get(cmd)

                    if not command_handler:
                        await to_thread(print, f"Comando desconocido: {cmd}")

                    else:
                        await command_handler(args)
                    continue

                await self.next(user_input)
        except KeyboardInterrupt:
            pass
