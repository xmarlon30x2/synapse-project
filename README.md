Synapse AI

https://img.shields.io/badge/License-MIT-yellow.svg
https://img.shields.io/badge/python-3.13+-blue.svg
https://img.shields.io/badge/code%20style-black-000000.svg

Synapse AI es un framework modular y flexible para construir agentes conversacionales potenciados por modelos de lenguaje (LLMs) y herramientas externas, utilizando el Model Context Protocol (MCP). Diseñado para ser simple de usar pero altamente extensible, te permite conectar tu agente a cualquier API compatible con OpenAI (OpenRouter, OpenAI, proveedores locales, etc.) y a servidores MCP que exponen herramientas como sistema de archivos, búsqueda web, bases de datos y más.

---

✨ Características

· Arquitectura limpia y desacoplada: Separación clara entre agente, memoria, modelo y contexto (gestión de herramientas).
· Soporte nativo para herramientas MCP: Conecta múltiples servidores MCP y el agente podrá invocar sus herramientas automáticamente.
· Streaming en tiempo real: Observa la generación de la respuesta token por token, incluyendo las llamadas a herramientas y sus resultados.
· Memoria persistente: La conversación se guarda automáticamente en un archivo JSON y se restaura al reiniciar.
· CLI interactiva con comandos integrados: Usa /help, /clear, /exit, /send para gestionar la conversación fácilmente.
· Totalmente asíncrono: Construido con asyncio para un rendimiento óptimo en operaciones de E/S.
· Fácilmente extensible: Puedes crear tus propias implementaciones de memoria, modelo o contexto.

---

📦 Instalación

Opción 1: Instalación desde PyPI (cuando esté publicado)

```bash
pip install synapse-ai
```

Opción 2: Instalación desde el repositorio

```bash
git clone https://github.com/xmarlon30x2/synapse-ai.git
cd synapse-ai
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -e .
```

Requisitos

· Python 3.13 o superior.
· Una clave de API para el proveedor de modelos (OpenRouter, OpenAI, etc.)

---

⚙️ Configuración

Crea un archivo .env en el directorio de trabajo (o define la variable de entorno SYNAPSE_APIKEY) con tu clave de API:

```env
SYNAPSE_APIKEY=sk-or-v1-...
```

Además, necesitas dos archivos JSON (puedes cambiar sus rutas con argumentos de línea de comandos):

1. Contexto de herramientas (synapse-context.json)

Define los servidores MCP que el agente puede utilizar. Ejemplo con el servidor de sistema de archivos:

```json
{
  "servers": [
    {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/ruta/a/tu/directorio"],
      "env": {}
    }
  ]
}
```

Cada servidor debe ser un ejecutable que implemente el protocolo MCP sobre stdio.

2. Archivo de memoria (synapse-memory.json)

Se crea automáticamente y almacena el historial de la conversación. No es necesario editarlo manualmente.

---

🚀 Uso

Una vez instalado, ejecuta la CLI con:

```bash
synapse-cli [opciones]
```

Opciones disponibles

Opción Descripción
--context-filename Ruta al JSON de configuración del contexto (por defecto ./synapse-context.json)
--memory-filename Ruta al archivo de memoria (por defecto ./synapse-memory.json)
--api-key Clave de API (sobrescribe la variable de entorno SYNAPSE_APIKEY)
--base-url URL base del proveedor de IA (por defecto https://openrouter.ai/api/v1)
--model Nombre del modelo (por defecto openrouter/aurora-alpha)

Ejemplo

```bash
synapse-cli --model openai/gpt-4o --base-url https://api.openai.com/v1
```

Al iniciar, verás el prompt interactivo:

```
Welcome to Synapse CLI!

Write /help to show help
Write anything to run the agent

user>
```

Comandos integrados

Comando Descripción
/exit Sale del programa.
/help Muestra esta ayuda.
/clear Borra todo el historial de la conversación.
/send <msg> Envía un mensaje al agente sin ejecutarlo (solo lo almacena en memoria).

Todo lo que no empiece con / se envía al agente, que lo procesa y transmite la respuesta en tiempo real.

---

🧠 Ejemplo de interacción

```
user> ¿Qué archivos hay en el directorio actual?
(call:call_abc123) list_directory> { "path": "." }
(tool:call_abc123) ["README.md", "src", "pyproject.toml"]
En el directorio actual encuentro los archivos README.md, la carpeta src y pyproject.toml.
```

Durante la respuesta, los tokens de texto aparecen en línea, y las llamadas a herramientas se muestran con su ID y resultados.

---

🏗️ Arquitectura del proyecto

Synapse AI se compone de cuatro módulos principales:

· Agent: Orquesta el ciclo de conversación. Decide cuándo invocar al modelo y cuándo ejecutar herramientas.
· Memory: Almacena todos los mensajes (usuario, asistente, herramientas). La implementación por defecto usa un archivo JSON.
· Model: Encapsula la comunicación con la API del LLM. Maneja streaming y conversión de formatos.
· Context: Gestiona las conexiones a servidores MCP. Provee las definiciones de herramientas y ejecuta las llamadas.

Flujo típico:

1. La entrada del usuario se guarda en memoria.
2. El agente invoca al modelo en modo streaming.
3. Si el modelo genera llamadas a herramientas, el contexto las ejecuta y los resultados se añaden como mensajes de herramienta.
4. El agente vuelve a llamar al modelo con esos resultados para obtener la respuesta final.
5. La respuesta final se transmite al usuario.

---

🛠️ Desarrollo

Si deseas contribuir o modificar el código:

1. Clona el repositorio e instala en modo editable (como se indicó arriba).
2. Asegúrate de tener las herramientas de desarrollo:
   ```bash
   pip install black ruff mypy
   ```
3. El código sigue las configuraciones de pyproject.toml:
   · Formato: black src/
   · Linting: ruff check src/
   · Tipado: mypy src/

Ejecuta todas las comprobaciones antes de enviar un Pull Request.

---

📄 Licencia

Distribuido bajo la licencia MIT. Ver LICENSE para más información.

---

🔗 Enlaces

· Repositorio en GitHub
· Documentación
· Issues

---

¿Preguntas o sugerencias? No dudes en abrir un issue. ¡Las contribuciones son bienvenidas!