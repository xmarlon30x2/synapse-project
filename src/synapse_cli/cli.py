import asyncio
from collections.abc import Callable
from types import CoroutineType
from typing import Any

from synapse_core.agent import Agent
from synapse_core.types import (
    TextToken,
    ToolCallArgumentsToken,
    ToolCallIDToken,
    ToolCallNameToken,
    ToolMessage,
    UserMessage,
)

type Command = Callable[[str], CoroutineType[Any, Any, None]]


class SynapseCli:
    """
    Interfaz de línea de comandos para interactuar con el agente.
    Procesa la entrada del usuario, reconoce comandos especiales (prefijo '/')
    y muestra la salida del agente en tiempo real.
    """

    def __init__(self, agent: Agent) -> None:
        self.agent: Agent = agent
        self.prompt = "user> "
        # Registro de comandos internos
        self.command_registry: dict[str, Command] = {
            "exit": self.exit,
            "send": self.send,
            "help": self.help,
        }

    async def exit(self, arg: str):
        """Comando para salir del programa."""
        raise KeyboardInterrupt()

    async def help(self, arg: str) -> None:
        """Comando para mostrar ayuda."""
        for name, command in self.command_registry.items():
            await asyncio.to_thread(print, f"/{name:<10s} {command.__doc__ or ''}")

    async def send(self, arg: str) -> None:
        """Comando para enviar un mensaje al agente sin ejecutarlo."""
        user_message = UserMessage(content=arg)
        await self.agent.memory.add(message=user_message)

    async def callback(self, user_input: str) -> None:
        """
        Procesa una entrada del usuario (no comando) y muestra la respuesta del agente.
        """
        # Guardamos el mensaje del usuario
        await self.send(arg=user_input)

        # Iteramos sobre el stream del agente
        async for chunk in self.agent.next_stream():
            if isinstance(chunk, TextToken):
                # Imprimimos texto en la misma línea
                await asyncio.to_thread(print, chunk.text, flush=True, end="")

            elif isinstance(chunk, ToolCallIDToken):
                # Mostramos el inicio de una llamada a herramienta
                await asyncio.to_thread(
                    print, f"\n(call:{chunk.id})", flush=True, end=""
                )

            elif isinstance(chunk, ToolCallNameToken):
                # Mostramos el nombre de la herramienta
                await asyncio.to_thread(print, f" {chunk.name}> ", flush=True, end="")

            elif isinstance(chunk, ToolCallArgumentsToken):
                # Mostramos los argumentos (pueden venir fragmentados)
                await asyncio.to_thread(print, chunk.arguments, flush=True, end="")

            elif isinstance(chunk, ToolMessage):
                # Mostramos el resultado de la herramienta
                await asyncio.to_thread(
                    print, f"\n(tool:{chunk.call_id})", chunk.content, flush=True
                )

        # Línea en blanco después de la respuesta completa
        await asyncio.to_thread(print, "\n")

    async def loop(self) -> None:
        """
        Bucle principal de la CLI: lee entrada del usuario, maneja comandos
        o llama a callback() para procesar la entrada.
        """
        await asyncio.to_thread(print, "Welcome to Synapse CLI! write /help for show help")
        try:
            while True:
                # Leer entrada del usuario (en hilo separado para no bloquear)
                user_input: str = await asyncio.to_thread(input, self.prompt)

                if not user_input:
                    continue

                # Si comienza con '/', es un comando interno
                if user_input.startswith("/"):
                    cmd, *args = user_input[1:].strip().split(maxsplit=1)
                    args = args[0] if args else ""
                    command_handler: Command | None = self.command_registry.get(cmd)

                    if not command_handler:
                        await asyncio.to_thread(print, f"Comando desconocido: {cmd}")
                    else:
                        await command_handler(args)
                    continue

                # Entrada normal del usuario
                await self.callback(user_input=user_input)
        except KeyboardInterrupt:
            # Salida limpia con Ctrl+C
            pass
