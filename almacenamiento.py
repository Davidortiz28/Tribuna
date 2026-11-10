"""Lectura, validación, escritura y consulta de los archivos JSON."""

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4


SENTIMIENTOS_VALIDOS = {"positivo", "negativo", "neutro", "mixto"}
VERSION_DATOS = 1


def cargar_jugadores(ruta: str | Path) -> list[dict[str, str]]:
    """Lee el catálogo y valida su estructura e identificadores."""
    ruta_archivo = Path(ruta)

    try:
        with ruta_archivo.open("r", encoding="utf-8") as archivo:
            contenido: Any = json.load(archivo)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(
            f"El catálogo de jugadores no contiene JSON válido: {ruta_archivo}"
        ) from error

    if not isinstance(contenido, dict) or contenido.get("version") != VERSION_DATOS:
        raise ValueError("El catálogo debe ser un objeto JSON con version igual a 1.")

    jugadores = contenido.get("jugadores")
    if not isinstance(jugadores, list):
        raise ValueError("El campo 'jugadores' debe ser una lista.")

    ids_vistos: set[str] = set()
    for indice, jugador in enumerate(jugadores, start=1):
        if not isinstance(jugador, dict):
            raise ValueError(f"El jugador número {indice} debe ser un objeto JSON.")

        for campo in ("id", "nombre", "pais"):
            valor = jugador.get(campo)
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(
                    f"El jugador número {indice} debe tener '{campo}' como texto no vacío."
                )

        jugador_id = jugador["id"]
        if jugador_id in ids_vistos:
            raise ValueError(f"El identificador de jugador '{jugador_id}' está repetido.")
        ids_vistos.add(jugador_id)

    return jugadores


def cargar_opiniones(ruta: str | Path) -> dict[str, Any]:
    """Carga y valida el documento persistente de opiniones.

    Si el archivo todavía no existe, devuelve la estructura vacía inicial, pero
    no crea el archivo hasta que se guarde una opinión.
    """
    return _leer_documento_opiniones(Path(ruta))


def crear_registro(
    jugador: dict[str, str],
    texto: str,
    analisis: Any,
    modelo: str,
    version_prompt: str = "1.0",
) -> dict[str, Any]:
    """Combina la opinión original, el análisis y los metadatos del registro.

    ``analisis`` será el objeto Pydantic que implementaremos en ``analisis.py``.
    Solo se permite crear registros para opiniones pertinentes y clasificadas.
    """
    if not isinstance(texto, str) or not 5 <= len(texto.strip()) <= 1000:
        raise ValueError("La opinión debe tener entre 5 y 1000 caracteres no blancos.")

    for campo in ("id", "nombre"):
        valor = jugador.get(campo)
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"El jugador debe tener el campo '{campo}' como texto no vacío.")

    es_pertinente = _obtener_campo(analisis, "es_pertinente")
    sentimiento = _obtener_campo(analisis, "sentimiento")
    razon = _obtener_campo(analisis, "razon")
    if es_pertinente is not True:
        raise ValueError("No se puede guardar una opinión no pertinente.")
    if sentimiento not in SENTIMIENTOS_VALIDOS:
        raise ValueError("El análisis no contiene un sentimiento válido.")
    if not isinstance(razon, str) or not 1 <= len(razon.strip()) <= 300:
        raise ValueError("La razón debe tener entre 1 y 300 caracteres.")
    if not isinstance(modelo, str) or not modelo.strip():
        raise ValueError("El nombre del modelo debe ser un texto no vacío.")
    if not isinstance(version_prompt, str) or not version_prompt.strip():
        raise ValueError("La versión del prompt debe ser un texto no vacío.")

    registro = {
        "id": str(uuid4()),
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "jugador_id": jugador["id"],
        "jugador_nombre": jugador["nombre"],
        "opinion_original": texto,
        "sentimiento": sentimiento,
        "razon": razon,
        "modelo": modelo,
        "version_prompt": version_prompt,
    }
    _validar_registro(registro)
    return registro


def guardar_opinion(ruta: str | Path, registro: dict[str, Any]) -> bool:
    """Añade una opinión con reemplazo atómico y conserva los registros previos.

    Devuelve ``True`` si se guardó. Devuelve ``False`` si el mismo registro ya
    existía, lo que permite reintentar una escritura sin duplicarlo. Un ID
    existente con contenido distinto se considera un error.
    """
    _validar_registro(registro)
    ruta_archivo = Path(ruta)
    documento = _leer_documento_opiniones(ruta_archivo)
    existentes = documento["opiniones"]

    for existente in existentes:
        if existente["id"] == registro["id"]:
            if existente == registro:
                return False
            raise ValueError(
                f"El ID de opinión '{registro['id']}' ya existe con otros datos."
            )

    documento["opiniones"].append(registro)
    ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
    ruta_temporal: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=ruta_archivo.parent,
            prefix=f".{ruta_archivo.name}.",
            suffix=".tmp",
            delete=False,
        ) as archivo_temporal:
            ruta_temporal = archivo_temporal.name
            json.dump(documento, archivo_temporal, ensure_ascii=False, indent=2)
            archivo_temporal.write("\n")
            archivo_temporal.flush()
            os.fsync(archivo_temporal.fileno())

        os.replace(ruta_temporal, ruta_archivo)
        ruta_temporal = None
        return True
    finally:
        if ruta_temporal is not None:
            try:
                os.unlink(ruta_temporal)
            except FileNotFoundError:
                pass


def consultar_opiniones(
    registros: list[dict[str, Any]],
    jugador_id: str | None = None,
    sentimiento: str | None = None,
) -> list[dict[str, Any]]:
    """Filtra registros en memoria sin realizar llamadas al modelo."""
    if sentimiento is not None and sentimiento not in SENTIMIENTOS_VALIDOS:
        raise ValueError(f"Sentimiento no reconocido: {sentimiento}")

    return [
        registro
        for registro in registros
        if (jugador_id is None or registro.get("jugador_id") == jugador_id)
        and (sentimiento is None or registro.get("sentimiento") == sentimiento)
    ]


def _leer_documento_opiniones(ruta: Path) -> dict[str, Any]:
    """Lee el archivo existente; nunca reemplaza datos dañados por defecto."""
    if not ruta.exists():
        return {"version": VERSION_DATOS, "opiniones": []}

    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            documento: Any = json.load(archivo)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError(f"El archivo de opiniones contiene JSON inválido: {ruta}") from error

    if (
        not isinstance(documento, dict)
        or type(documento.get("version")) is not int
        or documento.get("version") != VERSION_DATOS
        or not isinstance(documento.get("opiniones"), list)
    ):
        raise ValueError(f"El archivo de opiniones no cumple el esquema esperado: {ruta}")

    ids_vistos: set[str] = set()
    for indice, registro in enumerate(documento["opiniones"], start=1):
        try:
            _validar_registro(registro)
        except ValueError as error:
            raise ValueError(f"Registro de opinión número {indice} inválido: {error}") from error
        if registro["id"] in ids_vistos:
            raise ValueError(f"El archivo contiene el ID repetido '{registro['id']}'.")
        ids_vistos.add(registro["id"])

    return documento


def _validar_registro(registro: Any) -> None:
    """Valida los campos y tipos requeridos por el contrato persistente."""
    if not isinstance(registro, dict):
        raise ValueError("Cada opinión debe ser un objeto JSON.")

    campos_texto = (
        "id",
        "fecha_utc",
        "jugador_id",
        "jugador_nombre",
        "opinion_original",
        "sentimiento",
        "razon",
        "modelo",
        "version_prompt",
    )
    for campo in campos_texto:
        if not isinstance(registro.get(campo), str):
            raise ValueError(f"El campo '{campo}' debe ser texto.")

    try:
        UUID(registro["id"])
    except ValueError as error:
        raise ValueError("El campo 'id' debe ser un UUID válido.") from error

    try:
        fecha = datetime.fromisoformat(registro["fecha_utc"].replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("El campo 'fecha_utc' debe ser una fecha ISO 8601 válida.") from error
    if fecha.tzinfo is None or fecha.utcoffset() != timedelta(0):
        raise ValueError("El campo 'fecha_utc' debe incluir la zona horaria UTC.")

    if not registro["jugador_id"].strip() or not registro["jugador_nombre"].strip():
        raise ValueError("El ID y el nombre del jugador no pueden estar vacíos.")
    if not 5 <= len(registro["opinion_original"].strip()) <= 1000:
        raise ValueError("La opinión debe tener entre 5 y 1000 caracteres no blancos.")
    if registro["sentimiento"] not in SENTIMIENTOS_VALIDOS:
        raise ValueError("El campo 'sentimiento' no pertenece a las categorías permitidas.")
    if not 1 <= len(registro["razon"].strip()) <= 300:
        raise ValueError("La razón debe tener entre 1 y 300 caracteres.")
    for campo in ("modelo", "version_prompt"):
        if not registro[campo].strip():
            raise ValueError(f"El campo '{campo}' no puede estar vacío.")


def _obtener_campo(objeto: Any, campo: str) -> Any:
    """Permite leer un campo de un objeto Pydantic o de un diccionario."""
    if isinstance(objeto, dict):
        return objeto.get(campo)
    return getattr(objeto, campo, None)
