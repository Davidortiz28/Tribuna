# Registro de pruebas — Tribuna Global

Fecha de revisión: 9 de noviembre de 2026. Entorno: Python 3.14.2, Streamlit 1.67.0, LangChain Core 1.7.6, LangChain OpenAI 1.7.4, Pydantic 2.14.3 y python-dotenv 1.2.4. Migración a Groq revisada el 10 de noviembre de 2026.

## Resultados ejecutados

| Área | Prueba | Resultado observado | Estado |
|---|---|---|---|
| Catálogo | Cargar `jugadores.json` y contar IDs | Se cargaron 20 jugadores; los IDs son únicos. | Pasó |
| Datos de demostración | Validar `opiniones.json` | Se cargaron 12 registros ficticios de cuatro jugadores; hay ejemplos de las cuatro categorías. | Pasó |
| Persistencia | Guardar un registro de prueba en un proceso Python y leerlo desde un segundo proceso | El segundo proceso recuperó el registro escrito por el primero. El archivo temporal de prueba se retiró y `opiniones.json` de demostración no se modificó. | Pasó |
| Consulta combinada | Filtrar la interfaz por Messi (`j001`) y sentimiento positivo | AppTest mostró 1 opinión filtrada, 1 positiva, 0 en las otras categorías y una tabla con un resultado. | Pasó |
| Interfaz | Cargar la app con AppTest | Se mostró el título, el selector con 20 jugadores y las pestañas; no hubo excepciones de la aplicación. | Pasó |
| Validación de entrada | Enviar texto por debajo del mínimo en AppTest | Se rechazó antes del análisis y se conservó para corregirlo. | Pasó |
| Conversación | Cambiar jugador y usar «Nueva conversación» en AppTest | Cada mensaje conservó el jugador capturado; limpiar el chat no borró los datos persistidos. | Pasó |
| Guardado y reintento | Ejecutar el flujo con análisis simulado en AppTest | Se guardó una vez; el reintento con el mismo registro no creó duplicados. | Pasó con simulación |
| JSON dañado | Intentar cargar un archivo de opiniones inválido de prueba | Se informó el error y el archivo inválido permaneció intacto. | Pasó |
| Configuración de proveedor | Analizador simulado verificó `GROQ_API_KEY`, `GROQ_MODEL`, endpoint compatible y esquema Pydantic con el modo JSON Schema. No se hizo llamada de red en esa revisión. | Pasó sin red |
| Descarga | Revisar la vista de consulta | El control de descarga JSON está disponible con los resultados filtrados. | Pasó |

## Pruebas pendientes o limitadas

| Prueba | Motivo / resultado |
|---|---|
| Llamada real de clasificación con Groq | Se recibió un HTTP 400 al usar `function_calling`: el proveedor rechazó la invocación de herramienta. El analizador se cambió a JSON Schema, que Groq documenta para `openai/gpt-oss-20b`; falta comprobarlo con otra opinión. | Pendiente de reintento |
| Manejo del error de API | En la etapa anterior, OpenAI respondió HTTP 429 por saldo agotado; la interfaz conservó el texto pendiente y no simuló una clasificación. Groq aún no se ha llamado. |
| Fallo real de permisos de escritura | No se simuló un directorio protegido en este entorno. El manejador conserva el registro pendiente y solo confirma después de guardar. |
| Captura de pantalla tras reiniciar Streamlit | La persistencia del almacenamiento se comprobó entre procesos independientes; falta adjuntar una captura visual del navegador abierto tras un reinicio. |

## Evidencia visual que se puede capturar localmente

1. En **Consultar opiniones**, filtrar por Lionel Messi y **Positivo**. Debe aparecer una opinión filtrada y un conteo positivo de 1. Capturar esa vista.
2. Detener Streamlit con `Ctrl+C` y volver a iniciar `streamlit run app.py` desde la carpeta del proyecto. Abrir **Consultar opiniones** y comprobar que los registros del JSON siguen visibles. Capturar esa vista.

Los registros iniciales son ficticios. Estas capturas muestran persistencia del catálogo de demostración; para probar una opinión real de usuario se necesita que la API pueda procesar y guardar el envío.
