"""Interfaz Streamlit para emitir opiniones sobre futbolistas."""

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st

from analisis import VERSION_PROMPT, analizar_opinion
from almacenamiento import (
    cargar_jugadores,
    cargar_opiniones,
    consultar_opiniones,
    crear_registro,
    guardar_opinion,
)


BASE_DIR = Path(__file__).resolve().parent
RUTA_JUGADORES = BASE_DIR / "datos" / "jugadores.json"
RUTA_OPINIONES = BASE_DIR / "datos" / "opiniones.json"


def _agregar_mensaje(
    rol: str,
    contenido: str,
    jugador: dict[str, str],
    mensaje_id: str | None = None,
) -> str:
    """Guarda un mensaje en la sesión junto con el jugador al que se refiere."""
    identificador = mensaje_id or str(uuid4())
    st.session_state["historial_chat"].append(
        {
            "id": identificador,
            "role": rol,
            "content": contenido,
            "jugador_id": jugador["id"],
            "jugador_nombre": jugador["nombre"],
        }
    )
    return identificador


def _mostrar_mensaje(mensaje: dict[str, Any]) -> None:
    """Dibuja un mensaje del historial con el jugador asociado."""
    with st.chat_message(mensaje["role"]):
        if mensaje["role"] == "user":
            st.caption(f"Opinión sobre {mensaje['jugador_nombre']}")
        st.markdown(mensaje["content"])


def _procesar_envio_pendiente() -> None:
    """Analiza y guarda el envío actual, conservándolo si ocurre un error."""
    pendiente = st.session_state.get("envio_pendiente")
    if pendiente is None:
        return

    texto = pendiente["texto"]
    jugador = pendiente["jugador"]
    longitud = len(texto.strip()) if isinstance(texto, str) else 0
    if not 5 <= longitud <= 1000:
        _agregar_mensaje(
            "assistant",
            "La opinión debe tener entre 5 y 1000 caracteres después de quitar "
            "los espacios exteriores. No se llamó al modelo ni se guardó el texto.",
            jugador,
        )
        return

    registro = pendiente.get("registro")
    if registro is None:
        try:
            with st.spinner("Analizando la opinión..."):
                analisis = analizar_opinion(jugador, texto)
        except Exception as error:
            _agregar_mensaje(
                "assistant",
                "No se pudo analizar la opinión. El texto permanece disponible para "
                f"reintentar. Detalle: {type(error).__name__}: {error}",
                jugador,
            )
            return

        if not analisis.es_pertinente:
            _agregar_mensaje(
                "assistant",
                "El mensaje no parece ser una opinión sobre "
                f"{jugador['nombre']}, por eso no se guardó. "
                f"{analisis.razon}",
                jugador,
            )
            st.session_state["envio_pendiente"] = None
            return

        try:
            nombre_modelo = os.getenv("GROQ_MODEL", "").strip()
            registro = crear_registro(
                jugador=jugador,
                texto=texto,
                analisis=analisis,
                modelo=nombre_modelo,
                version_prompt=VERSION_PROMPT,
            )
        except Exception as error:
            _agregar_mensaje(
                "assistant",
                "El análisis se completó, pero no se pudo preparar el registro. "
                "La opinión permanece disponible para reintentar. "
                f"Detalle: {type(error).__name__}: {error}",
                jugador,
            )
            return

        # Se conserva el mismo UUID si falla la escritura y el usuario reintenta.
        pendiente["registro"] = registro
        st.session_state["envio_pendiente"] = pendiente

    try:
        se_guardo = guardar_opinion(RUTA_OPINIONES, registro)
    except Exception as error:
        _agregar_mensaje(
            "assistant",
            "El análisis terminó, pero no se pudo guardar la opinión. El registro "
            "calculado permanece disponible para reintentar sin volver a llamar "
            f"al modelo. Detalle: {type(error).__name__}: {error}",
            jugador,
        )
        return

    estado_guardado = (
        "Opinión guardada correctamente."
        if se_guardo
        else "Este registro ya estaba guardado; no se creó un duplicado."
    )
    _agregar_mensaje(
        "assistant",
        f"**Sentimiento:** {registro['sentimiento']}\n\n"
        f"**Razón:** {registro['razon']}\n\n{estado_guardado}",
        jugador,
    )
    st.session_state["envio_pendiente"] = None


st.set_page_config(page_title="Tribuna Global", page_icon="⚽", layout="wide")

st.session_state.setdefault("historial_chat", [])
st.session_state.setdefault("envio_pendiente", None)

try:
    jugadores = cargar_jugadores(RUTA_JUGADORES)
except (OSError, ValueError) as error:
    st.error(f"No se pudo cargar el catálogo de futbolistas: {error}")
    st.stop()

if not jugadores:
    st.error("El catálogo no contiene futbolistas para seleccionar.")
    st.stop()

jugadores_por_id = {jugador["id"]: jugador for jugador in jugadores}

with st.sidebar:
    st.header("Jugador")
    jugador_id = st.selectbox(
        "Selecciona un futbolista",
        options=list(jugadores_por_id),
        format_func=lambda identificador: (
            f"{jugadores_por_id[identificador]['nombre']} — "
            f"{jugadores_por_id[identificador]['pais']}"
        ),
        key="jugador_seleccionado_id",
    )
    if st.button("Nueva conversación", width="stretch"):
        # Solo se limpia el historial visual; el archivo persistente no se toca.
        st.session_state["historial_chat"] = []

st.title("Tribuna Global")
st.write(
    "Comparte tu opinión sobre un futbolista. El sistema analizará únicamente "
    "ese mensaje y conservará el texto original junto con su clasificación."
)

tab_emitir, tab_consultar = st.tabs(["Emitir opinión", "Consultar opiniones"])

with tab_emitir:
    st.subheader("Emitir opinión")

    for mensaje in st.session_state["historial_chat"]:
        _mostrar_mensaje(mensaje)

    pendiente = st.session_state.get("envio_pendiente")
    if pendiente is not None:
        jugador_pendiente = pendiente["jugador"]
        registro_pendiente = pendiente.get("registro")
        with st.container(border=True):
            st.markdown("**Opinión pendiente de completar**")
            st.caption(
                f"Jugador asociado al envío: {jugador_pendiente['nombre']} "
                f"({jugador_pendiente['pais']})"
            )
            texto_editado = st.text_area(
                "Texto que se conservará",
                value=pendiente["texto"],
                key=f"opinion_pendiente_{pendiente['token']}",
                height=100,
                disabled=registro_pendiente is not None,
            )
            if st.button(
                "Reintentar",
                key=f"reintentar_{pendiente['token']}",
                width="stretch",
            ):
                pendiente["texto"] = texto_editado
                mensaje_usuario = next(
                    (
                        mensaje
                        for mensaje in st.session_state["historial_chat"]
                        if mensaje["id"] == pendiente["mensaje_id"]
                    ),
                    None,
                )
                if mensaje_usuario is None:
                    pendiente["mensaje_id"] = _agregar_mensaje(
                        "user", texto_editado, jugador_pendiente
                    )
                else:
                    mensaje_usuario["content"] = texto_editado
                st.session_state["envio_pendiente"] = pendiente
                _procesar_envio_pendiente()
                st.rerun()

    texto_nuevo = st.chat_input(
        "Escribe tu opinión (5 a 1000 caracteres)",
        disabled=pendiente is not None,
    )

    if texto_nuevo is not None:
        jugador_actual = jugadores_por_id[jugador_id]
        jugador_capturado = {
            "id": jugador_actual["id"],
            "nombre": jugador_actual["nombre"],
            "pais": jugador_actual["pais"],
        }
        mensaje_id = _agregar_mensaje("user", texto_nuevo, jugador_capturado)
        st.session_state["envio_pendiente"] = {
            "token": str(uuid4()),
            "texto": texto_nuevo,
            "jugador": jugador_capturado,
            "mensaje_id": mensaje_id,
            "registro": None,
        }
        _procesar_envio_pendiente()
        st.rerun()

with tab_consultar:
    st.subheader("Consultar opiniones")
    st.info(
        "El archivo incluye 12 opiniones ficticias para demostración. "
        "No son envíos reales de usuarios ni resultados verificados."
    )
    try:
        documento_opiniones = cargar_opiniones(RUTA_OPINIONES)
    except (OSError, ValueError) as error:
        st.error(f"No se pudieron cargar las opiniones: {error}")
    else:
        registros = documento_opiniones["opiniones"]
        col_jugador, col_sentimiento = st.columns(2)

        with col_jugador:
            filtro_jugador = st.selectbox(
                "Filtrar por jugador",
                options=[None, *jugadores_por_id],
                format_func=lambda identificador: (
                    "Todos los jugadores"
                    if identificador is None
                    else (
                        f"{jugadores_por_id[identificador]['nombre']} — "
                        f"{jugadores_por_id[identificador]['pais']}"
                    )
                ),
                key="filtro_jugador_opiniones",
            )

        sentimientos = ("positivo", "negativo", "neutro", "mixto")
        with col_sentimiento:
            filtro_sentimiento = st.selectbox(
                "Filtrar por sentimiento",
                options=[None, *sentimientos],
                format_func=lambda valor: (
                    "Todos los sentimientos" if valor is None else valor.capitalize()
                ),
                key="filtro_sentimiento_opiniones",
            )

        registros_filtrados = consultar_opiniones(
            registros,
            jugador_id=filtro_jugador,
            sentimiento=filtro_sentimiento,
        )

        conteos = {
            sentimiento: sum(
                registro["sentimiento"] == sentimiento
                for registro in registros_filtrados
            )
            for sentimiento in sentimientos
        }
        metricas = st.columns(5)
        metricas[0].metric("Opiniones filtradas", len(registros_filtrados))
        for columna, sentimiento in zip(metricas[1:], sentimientos):
            columna.metric(sentimiento.capitalize(), conteos[sentimiento])

        if registros_filtrados:
            filas_tabla = [
                {
                    "Fecha UTC": registro["fecha_utc"],
                    "Jugador": registro["jugador_nombre"],
                    "Opinión original": registro["opinion_original"],
                    "Sentimiento": registro["sentimiento"],
                    "Razón": registro["razon"],
                }
                for registro in registros_filtrados
            ]
            st.dataframe(filas_tabla, hide_index=True, width="stretch")
        else:
            st.info("No hay opiniones que coincidan con estos filtros.")

        json_filtrado = json.dumps(
            {"version": 1, "opiniones": registros_filtrados},
            ensure_ascii=False,
            indent=2,
        )
        st.download_button(
            "Descargar resultados filtrados como JSON",
            data=json_filtrado.encode("utf-8"),
            file_name="tribuna_global_opiniones.json",
            mime="application/json",
            width="stretch",
        )
