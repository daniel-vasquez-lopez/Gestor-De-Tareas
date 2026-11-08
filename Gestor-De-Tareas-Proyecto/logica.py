"""Reglas y almacenamiento del gestor de tareas, sin dependencias de la interfaz."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "tareas.json"
ESTADOS = ("Pendiente", "En progreso", "Completada")
PRIORIDADES = ("Alta", "Media", "Baja")


def validar_fecha(texto: str) -> str:
    """Valida y devuelve una fecha en el formato DD/MM/AAAA."""
    texto = texto.strip()
    if not texto:
        return ""
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValueError("La fecha debe estar en formato DD/MM/AAAA.")


def normalizar_tarea(datos: object, id_predeterminado: int) -> dict:
    """Valida campos y completa los que falten en una tarea."""
    if not isinstance(datos, dict):
        raise ValueError("Una tarea del archivo no tiene un formato válido.")
    nombre = str(datos.get("nombre", "")).strip()
    if not nombre:
        raise ValueError("Una tarea del archivo no tiene nombre.")
    try:
        identificador = int(datos.get("id", id_predeterminado))
    except (TypeError, ValueError):
        identificador = id_predeterminado
    if identificador < 1:
        identificador = id_predeterminado
    prioridad = str(datos.get("prioridad", "Media"))
    estado = str(datos.get("estado", "Pendiente"))
    return {
        "id": identificador,
        "nombre": nombre[:200],
        "descripcion": str(datos.get("descripcion", "")).strip()[:2000],
        "prioridad": prioridad if prioridad in PRIORIDADES else "Media",
        "estado": estado if estado in ESTADOS else "Pendiente",
        "fecha_limite": validar_fecha(str(datos.get("fecha_limite", ""))),
    }


def normalizar_lista(datos: object) -> list[dict]:
    """Valida una lista importada y repara identificadores duplicados."""
    if not isinstance(datos, list):
        raise ValueError("El archivo debe contener una lista de tareas.")
    tareas = []
    ids = set()
    for indice, elemento in enumerate(datos, start=1):
        tarea = normalizar_tarea(elemento, indice)
        if tarea["id"] in ids:
            tarea["id"] = max(ids, default=0) + 1
        ids.add(tarea["id"])
        tareas.append(tarea)
    return tareas


def cargar_tareas() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
    if not isinstance(datos, list):
        raise ValueError("tareas.json debe contener una lista de tareas.")
    return normalizar_lista(datos)


def guardar_archivo(tareas: list[dict], destino: Path = DATA_FILE) -> None:
    """Guarda de forma segura para evitar dejar un JSON incompleto."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destino.parent,
            suffix=".tmp", delete=False,
        ) as archivo:
            temporal = Path(archivo.name)
            json.dump(tareas, archivo, ensure_ascii=False, indent=2)
            archivo.write("\n")
        os.replace(temporal, destino)
    finally:
        if temporal and temporal.exists():
            temporal.unlink(missing_ok=True)


def fecha_de(tarea: dict) -> date | None:
    """Convierte la fecha límite de una tarea a date."""
    texto = tarea.get("fecha_limite", "")
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        return None


def categoria_fecha(tarea: dict, hoy: date | None = None) -> str:
    """Devuelve la categoría visual de vencimiento de una tarea."""
    fecha = fecha_de(tarea)
    if fecha is None:
        return ""
    if tarea["estado"] == "Completada":
        return "completada"
    dias = (fecha - (hoy or date.today())).days
    if dias < 0:
        return "vencida"
    if dias <= 3:
        return "proxima"
    return "normal"


def filtrar_tareas(
    tareas: list[dict], texto: str = "", estado: str = "Todos los estados",
    prioridad: str = "Todas las prioridades",
) -> list[dict]:
    """Busca, filtra y ordena tareas para presentarlas en la lista."""
    consulta = texto.strip().casefold()
    resultado = []
    for tarea in tareas:
        contenido = f"{tarea['nombre']} {tarea['descripcion']}".casefold()
        if consulta and consulta not in contenido:
            continue
        if estado != "Todos los estados" and tarea["estado"] != estado:
            continue
        if prioridad != "Todas las prioridades" and tarea["prioridad"] != prioridad:
            continue
        resultado.append(tarea)
    return sorted(
        resultado,
        key=lambda tarea: (
            tarea["estado"] == "Completada",
            fecha_de(tarea) or date.max,
            -tarea["id"],
        ),
    )


def resumen_tareas(tareas: list[dict]) -> dict[str, int]:
    """Calcula los contadores principales del panel."""
    completadas = sum(tarea["estado"] == "Completada" for tarea in tareas)
    return {
        "total": len(tareas),
        "active": len(tareas) - completadas,
        "overdue": sum(categoria_fecha(tarea) == "vencida" for tarea in tareas),
        "soon": sum(categoria_fecha(tarea) == "proxima" for tarea in tareas),
    }


def siguiente_id(tareas: list[dict]) -> int:
    return max((tarea["id"] for tarea in tareas), default=0) + 1


def guardar_tarea(tareas: list[dict], tarea: dict) -> list[dict]:
    """Devuelve la lista con la tarea nueva o con la existente actualizada."""
    if any(actual["id"] == tarea["id"] for actual in tareas):
        return [tarea if actual["id"] == tarea["id"] else actual for actual in tareas]
    return [*tareas, tarea]


def alternar_estado(tarea: dict) -> str:
    return "Pendiente" if tarea["estado"] == "Completada" else "Completada"


def eliminar_tarea(tareas: list[dict], identificador: int) -> list[dict]:
    return [tarea for tarea in tareas if tarea["id"] != identificador]
