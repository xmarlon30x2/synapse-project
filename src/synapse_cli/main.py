import argparse
import asyncio
from os import getenv
from pathlib import Path

from synapse_core.agent import Agent
from synapse_core.context import Context
from synapse_core.mappers import json_filename_to_context_config
from synapse_core.memory import JSONFileMemory
from synapse_core.model import Model
from synapse_core.types import ContextConfig

from .cli import SynapseCli


async def main() -> None:
    """
    Función principal de la CLI.
    Parsea argumentos, inicializa los componentes (memoria, modelo, contexto),
    crea el agente y ejecuta el bucle de la CLI.
    """
    parser = argparse.ArgumentParser(description="Agente de IA")
    parser.add_argument(
        "--context-filename",
        help="Ruta al JSON de configuración del contexto",
        default="./synapse-context.json",  # Nota: en el código original estaba intercambiado con memory-filename
    )
    parser.add_argument(
        "--memory-filename",
        help="Ruta al JSON de la memoria",
        default="./synapse-memory.json",
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

    # Inicializar memoria
    try:
        filename = Path(args.memory_filename)
        memory = JSONFileMemory(filename=filename)
    except Exception as exc:
        await asyncio.to_thread(print, f"Error cargando la memoria: {exc}")
        return

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
