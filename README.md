# Tribuna Global

Aplicación académica en Streamlit para recopilar opiniones de aficionados sobre futbolistas y clasificarlas en positivo, negativo, neutro o mixto mediante un modelo de lenguaje. La aplicación guarda el texto original junto con el resultado y permite consultar las opiniones por jugador y sentimiento.

El análisis es una clasificación automática de opiniones. No mide el rendimiento real de un jugador ni sustituye estadísticas, encuestas representativas o evaluación deportiva.

## Requisitos

- Python 3.11 o posterior.
- Una clave de API de Groq y acceso a un modelo habilitado para la cuenta.
- Conexión a internet para las llamadas de análisis.

La interfaz y la consulta local pueden abrirse sin una clave, pero enviar una opinión requiere una configuración válida.

## Instalación y configuración

La aplicación se conecta a Groq mediante su endpoint compatible con OpenAI. Por eso se mantiene `langchain-openai` como cliente de LangChain, aunque el proveedor configurado sea Groq. El modelo elegido es `openai/gpt-oss-20b`.

Desde la carpeta `tribuna_global`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env  # solo si .env todavía no existe
```

Si ya existe `.env` de una configuración anterior, edita ese mismo archivo y sustituye sus variables por estas; no lo sobrescribas con el archivo de ejemplo.

Edita `.env` y reemplaza los valores de ejemplo:

```dotenv
GROQ_API_KEY=tu_clave_de_groq
GROQ_MODEL=openai/gpt-oss-20b
```

No compartas el archivo `.env` ni guardes claves en el código. `.env` y `.venv` están excluidos de Git.

## Ejecución

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

En la pestaña **Emitir opinión**, selecciona un futbolista y escribe una opinión de 5 a 1000 caracteres. El análisis comprueba si el texto es pertinente y, si lo es, propone un sentimiento y una razón breve. La opinión pertinente se guarda en el archivo JSON. Si falla el análisis o el guardado, la interfaz conserva el texto para reintentar.

La selección de futbolista queda asociada al mensaje cuando se envía. **Nueva conversación** limpia el historial visible de chat; no borra las opiniones guardadas.

En **Consultar opiniones** se filtran los registros por futbolista, sentimiento o ambos. Se muestran los conteos del resultado filtrado y se puede descargar ese resultado como JSON.

## Datos y estructura

```text
tribuna_global/
├── app.py                 # Interfaz Streamlit y flujo de conversación
├── analisis.py            # Prompt y salida estructurada del modelo
├── almacenamiento.py      # Validación, persistencia y filtros JSON
├── .env.example           # Nombres de variables de configuración
├── requirements.txt       # Dependencias Python
└── datos/
    ├── jugadores.json     # Catálogo de futbolistas
    └── opiniones.json     # Opiniones y resultados persistidos
```

El catálogo contiene 20 jugadores con identificadores estables. Cada opinión guardada registra UUID, fecha UTC, jugador, texto original, sentimiento, razón, modelo y versión del prompt. El guardado conserva los registros existentes y reemplaza el archivo de forma atómica. Un archivo JSON dañado se informa como error y no se sobrescribe automáticamente.

`datos/opiniones.json` comienza con 12 opiniones **ficticias** para demostrar consultas y conteos: tres para cada uno de cuatro futbolistas, con ejemplos de las cuatro categorías. No provienen de personas ni de una llamada al modelo y no deben interpretarse como opiniones reales. La aplicación muestra esta aclaración en la consulta. Para iniciar sin ejemplos, se puede reemplazar su lista `opiniones` por una lista vacía manteniendo `"version": 1`.

## Criterios de clasificación

- **Positivo:** valoración favorable predominante.
- **Negativo:** valoración desfavorable predominante.
- **Neutro:** descripción o comentario sin una valoración clara.
- **Mixto:** aparecen valoraciones favorables y desfavorables relevantes.

La ironía y el sarcasmo pueden depender del contexto y ser ambiguos para un modelo. Una frase como «¡Qué precisión!» puede ser elogio literal o sarcasmo según el contexto; el sistema solo recibe el mensaje actual y el futbolista seleccionado. Cuando no hay una valoración clara, se prefiere neutral; cuando hay señales en ambas direcciones, mixto. La razón debe explicar brevemente la clasificación sin inventar estadísticas o hechos.

## Verificación realizada

En el entorno de desarrollo se verificaron:

- Persistencia entre dos procesos independientes: un registro escrito en el primero se leyó correctamente desde el segundo.
- Carga del catálogo y sus 20 identificadores únicos.
- Validación de registros, guardado, lectura, prevención de duplicados y filtros en almacenamiento.
- Conservación de un archivo de opiniones dañado sin reemplazar su contenido.
- Coherencia de la salida estructurada y construcción del prompt y la cadena de análisis.
- Flujo de interfaz con Streamlit AppTest y análisis/guardado simulados, incluida validación del texto, asociación al jugador y reinicio de conversación.
- Consulta con datos de ejemplo, conteos, filtrado por sentimiento y opción de descarga.
- Filtro combinado en la interfaz: Messi más positivo devolvió una opinión, con conteos coherentes.
- Persistencia comprobada al escribir un registro de prueba en un proceso y recuperarlo desde otro.

No se ha hecho todavía una llamada real a Groq con la configuración migrada. La clave y el modelo deben configurarse localmente. El plan gratuito tiene límites de uso que pueden cambiar; las clasificaciones reales aún no se presentan como validadas. Consulta [`evidencias/REGISTRO_PRUEBAS.md`](evidencias/REGISTRO_PRUEBAS.md) para resultados y pendientes.

AppTest no reportó excepciones de la aplicación, aunque el entorno mostró advertencias de contexto y un error de permisos al intentar limpiar una carpeta temporal externa al proyecto durante el cierre del proceso de prueba.

El entorno comprobado usó Python 3.14.2, Streamlit 1.67.0, LangChain Core 1.7.6, LangChain OpenAI 1.7.4, Pydantic 2.14.3 y python-dotenv 1.2.4. `langchain-openai` se utiliza como cliente compatible con Groq; no se instala un SDK adicional. `requirements.txt` permite instalar versiones compatibles más recientes.

## Privacidad y uso

Las opiniones se guardan localmente en `datos/opiniones.json`. No escribas información personal o sensible en los mensajes. Al enviar una opinión, su texto y el contexto del jugador se remiten al proveedor del modelo configurado para el análisis. Consulta las condiciones aplicables a esa cuenta y evita publicar el archivo de datos si contiene opiniones de usuarios.
