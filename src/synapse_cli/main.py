import argparse
import asyncio
from os import getenv
from pathlib import Path

from dotenv import load_dotenv

from synapse_core.agent import Agent
from synapse_core.context import Context
from synapse_core.mappers import json_filename_to_context_config
from synapse_core.model import Model
from synapse_core.types import ContextConfig

from .cli import SynapseCli


def main() -> None:
    """
    Función principal de la CLI.
    Parsea argumentos, inicializa los componentes (memoria, modelo, contexto),
    crea el agente y ejecuta el bucle de la CLI.
    """
    asyncio.run(async_main())


async def async_main() -> None:
    await asyncio.to_thread(load_dotenv, dotenv_path=".env")

    parser = argparse.ArgumentParser(description="Agente de IA")
    parser.add_argument(
        "--context-filename",
        help="Ruta al JSON de configuración del contexto",
        default="./synapse-context.json",  # Nota: en el código original estaba intercambiado con memory-filename
    )
    parser.add_argument(
        "--memory-type",
        default="sumarize-json-file",
        choices=["sumarize-json-file", "json-file"],
        help="Tipo de memoria a utilizar",
    )
    parser.add_argument(
        "--memory-filename",
        help="Ruta al JSON de la memoria",
        default="./synapse-memory.json",
    )
    parser.add_argument(
        "--memory-max-messages", help="Numero maximo de mensajes", default=60, type=int
    )
    parser.add_argument(
        "--memory-sumarize-message",
        help="Numero de mensajes a incluir en el resumen",
        default=10,
        type=int,
    )
    parser.add_argument(
        "--memory-sumarize-prompt",
        default="Resume toda nuestra converzacion en un mensaje conversacion, conservando la informacion clave:",
        help="Prompt personalizado para el resumen",
    )
    parser.add_argument(
        "--api-key", help="Clave de OpenRouter (o variable SYNAPSE_APIKEY)"
    )
    parser.add_argument(
        "--base-url",
        default="https://openrouter.ai/api/v1",
        help="URL base del proveedor de IA",
    )
    parser.add_argument(
        "--model", default="openrouter/aurora-alpha", help="Modelo a usar"
    )
    args = parser.parse_args()

    # Inicializar modelo
    try:
        model_name: str = args.model
        base_url: str = args.base_url
        api_key: str | None = args.api_key or getenv("SYNAPSE_APIKEY")

        if not api_key:
            raise ValueError("No se ha detectado la API KEY")

        model = Model(
            temperature=1,
            model=model_name,
            base_url=base_url,
            api_key=api_key,
        )
    except Exception as exc:
        await asyncio.to_thread(print, f"Error cargando el modelo: {exc}")
        return

    # Inicializar memoria
    try:
        filename = Path(args.memory_filename)

        if args.memory_type == "sumarize-json-file":
            from synapse_core.memoirs.summarizing_json_file_memory import (
                SummarizingJSONFileMemory,
            )

            memory = SummarizingJSONFileMemory(
                filename=filename,
                max_messages=args.memory_max_messages,
                sumarize_prompt=args.memory_sumarize_prompt,
                model=model,
                sumarize_message=args.memory_sumarize_message,
            )

        elif args.type == "json-file":
            from synapse_core.memoirs.json_file_memory import JSONFileMemory

            memory = JSONFileMemory(filename=filename)

        else:
            raise ValueError(f"Tipo de memoria no soportado: {args.type}")
    except Exception as exc:
        await asyncio.to_thread(print, f"Error cargando la memoria: {exc}")
        return

    # Inicializar contexto (conexiones MCP)
    try:
        # Cargar configuración del contexto desde JSON (en hilo separado)
        context_config: ContextConfig = await asyncio.to_thread(
            json_filename_to_context_config, json_filename=args.context_filename
        )
        context = Context(config=context_config)
    except Exception as exc:
        await asyncio.to_thread(print, f"Error iniciando el contexto: {exc}")
        return

    # Crear agente y CLI
    try:
        async with Agent(
            context=context,
            memory=memory,
            model=model,
        ) as agent:
            cli = SynapseCli(agent=agent)
            await cli.loop()
    except Exception as exc:
        await asyncio.to_thread(print, f"Error desconocido: {exc}")
