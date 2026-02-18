from collections import defaultdict

from .context import Context
from .memory import Memory
from .model import Model
from .types import AssistantMessage, TokenType, ToolCall

class Agent:
    def __init__(self, model: Model, memory: Memory, context: Context):
        # Guardamos el modelo
        self.model = model
        
        # Guardamos la memoria
        self.memory = memory
        
        # Guardamos el contexto
        self.context = context

    async def next_stream(self):
        # Esta funcion ejecutara el ciclo de vida del agente
        # e ira devolviendo los tokens y mensajes a medida que se vallan generando

        # Primero buscamos herramientas pendientes
        pending_tool_calls = await self.memory.next_pending_tool_calls()

        # No ejecutar el modelo si hay tareas pendientes
        model_dirty = not pending_tool_calls 
        
        # Marcar como sucio dependiendo si hay herramientas pendientes
        context_dirty = bool(pending_tool_calls)

        # Continuamos el ciclo si el modelo o el contexto esta sucio
        # Lo que queremos es que la primera vez siempre inicie
        # ya sea porque hay herramientas pendientes o porque sino se
        # marcara como sucio el modelo
        while model_dirty or context_dirty:
            # Si el modelo esta sucio ejecutar el modelo
            if model_dirty:
                # Obtenemos todos los mensajes de la memoria
                messages = await self.memory.all()

                # Creamos un buffer para el contenido del texto
                content = ''

                # Creamos un buffer para las llamadas a herramientas
                # Es un dicionario con las claves como indices y los valores como llamadas a herramientas
                # para poder acceder a cualquir llamada a herramienta sin importar el orden en el
                # que llegue el token
                tool_calls = defaultdict(lambda: ToolCall(id="", name="", arguments=""))

                # Creamos un chat en streaming con el modelo
                async for token in self.model.create_chat_stream(
                    # Le pasamos los mensajes
                    messages=messages,
                    # Y le pasamos las definiciones de las herramientas disponibles
                    # en el contexto
                    tool_definitions=self.context.tools_definitions
                ):
                    # Si el token es un texto
                    if token.type == TokenType.text:
                        # Guardamos el texto en el buffer de texto
                        content += token.text

                    # Si el token es un ID de una llamada a una herramienta
                    elif token.type == TokenType.tool_call_id:
                        # Guardamos el ID en la llamada a herramienta dependiendo del indice
                        # Si el indice no existe no importa porque tool_calls es un defaultdict
                        # y creara la llamada a herramienta solo
                        tool_calls[token.index].id += token.id

                    # Si el token es un nombre de una llamada a una herramienta
                    elif token.type == TokenType.tool_call_name:
                        # Guardamos el nombre en la llamada a herramienta dependiendo del indice
                        # igual que en el anterior tipo de token
                        tool_calls[token.index].name += token.name

                    # Si el token es un argumento de una llamada a una herramienta
                    elif token.type == TokenType.tool_call_arguments:
                        # Guardamos el argumento en la llamada a herramienta dependiendo del indice
                        # igual que en el anterior tipo de token
                        tool_calls[token.index].arguments += token.arguments

                    # Devolvemos el token
                    yield token

                # Si se genero texto o llamada a herramientas
                if content or tool_calls:
                    # Ordenar las llamada a herramientas por indice
                    tool_calls = [tool_call for _, tool_call in sorted(tool_calls.items(), key=lambda item: item[0])]
                    
                    # Crear el mensaje del asistente
                    assistant_message = AssistantMessage(
                        content=content,
                        tool_calls=tool_calls
                    )
                    
                    # Guardar el mensaje del asistente
                    await self.memory.add(assistant_message)

                    # Devolver el mensaje
                    yield assistant_message                    

                # Limpiar el modelo
                model_dirty = False
                # Si se usaron herramientas marcar como sucio al contexto
                # De no haberse usado herramientas el ciclo terminaria
                # ya que esta todo limpio
                context_dirty = bool(tool_calls) 

            # Si el contexto esta sucio ejecutar el contexto
            if context_dirty:
                # Usamos las herramientas pendientes creadas al inicio del ciclo
                # o buscamos denuevo en cazo de que no las tengamos ya
                pending_tool_calls = pending_tool_calls or await self.memory.next_pending_tool_calls()
                
                # Iteramos sobe todas las herramientas pendientes
                for tool_call in pending_tool_calls:
                    # Ejecutamos la herramienta
                    tool_message = await self.context.call_tool(tool_call)
                    
                    # Guardamos el resultado
                    await self.memory.add(tool_message)
                    
                    # Devolvemos el resultado
                    yield tool_message

                # Si habian herramientas pendientes marcamos el modelo como
                # sucio ya que tiene que procesar las respuestas
                model_dirty = bool(pending_tool_calls)

                # Despues de esto no quedaran herramientas pendientes
                # entonces limpiamos el contexto
                
                context_dirty = False
                # Borramos las herramientas pendietes actuales para 
                # Que en el proximo siclo use las nuevas
                pending_tool_calls = None
