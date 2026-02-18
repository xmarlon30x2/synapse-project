from openai import AsyncOpenAI

from .mappers import message_to_message_param, tool_definition_to_tool
from .types import (
    ChatIDToken,
    Message,
    TextToken,
    ToolCallArgumentsToken,
    ToolCallIDToken,
    ToolCallNameToken,
    ToolDefinition,
)


class Model:
    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 1):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature

    async def create_chat_stream(
        self,
        messages: list[Message],
        tool_definitions: list[ToolDefinition],
        store: bool | None = None,
        chat_id: str | None = None
    ):
        message_params = list(map(message_to_message_param, messages))
        tools = list(map(tool_definition_to_tool, tool_definitions))
        id_emited = False
        async for chunk in await self.client.chat.completions.create(
            messages=message_params,
            model=self.model,
            tools=tools,
            tool_choice="auto",
            temperature=self.temperature,
            stream=True,
            parallel_tool_calls=True,
            store=store,
            # chat_id = chat_id # algo como esto
        ):
            if not id_emited and not chat_id:
                id_emited = True
                yield ChatIDToken(id=chunk.id)

            delta = chunk.choices[0].delta

            if delta.content is not None:
                yield TextToken(delta.content)

            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if tool_call.id:
                        yield ToolCallIDToken(id=tool_call.id, index=tool_call.index)

                    if not tool_call.function:
                        continue

                    function = tool_call.function

                    if function.name:
                        yield ToolCallNameToken(
                            name=function.name, index=tool_call.index
                        )

                    if function.arguments:
                        yield ToolCallArgumentsToken(
                            arguments=function.arguments,
                            index=tool_call.index,
                        )
