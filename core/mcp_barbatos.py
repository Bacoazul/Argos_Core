"""
MCP tools: Barbatos — WoW: Forever (addon FeralHelper) ↔ Claude.

Toda la lógica vive en el Windows Bridge (paquete windows_bridge/barbatos): leer el
SavedVariables, escribir el buzón del addon y capturar la ventana del juego requieren
el host Windows. Acá solo hay envoltorios finos sobre /barbatos/* por HTTP.

Regla dura: nada toca el proceso del juego (sin teclas, sin memoria, sin live slots).
El juego escribe el SavedVariables solo con /reload, al salir o al cerrar → la foto
puede estar vieja; fh_status lo dice y sugiere /fh sync.
"""
from __future__ import annotations

import base64
from typing import Any
from urllib.parse import urlencode

from fastmcp.utilities.types import Image

from core.bridge_client import bridge_get, bridge_post
from core.mcp_server import mcp

def _query(**params: Any) -> str:
    clean = {k: v for k, v in params.items() if v not in (None, "")}
    return f"?{urlencode(clean)}" if clean else ""


@mcp.tool
def fh_status() -> dict[str, Any]:
    """
    Estado de Barbatos / WoW: Forever: si el juego está abierto, edad del archivo de
    guardado y de la foto de cada personaje (snapshot_age_s), zona y nivel, secciones
    disponibles y estado del buzón. Llamar primero. Si `hint` viene con texto, la foto
    está vieja: pedir al jugador que escriba /fh sync en el juego antes de responder
    sobre su estado actual.
    """
    return bridge_get("/barbatos/status")


@mcp.tool
def fh_snapshot(section: str | None = None, character: str | None = None) -> dict[str, Any]:
    """
    Lee la foto del personaje guardada por el addon FeralHelper.

    Args:
        section: una de personaje, ubicacion, bolsas, equipo, profesiones, misiones,
            reputaciones, hechizos, buffs, feralhelper. Sin sección devuelve la lista de secciones más
            personaje y ubicación (mapa = uiMapID, x/y en 0-100).
        character: nombre ("Kodiak") o clave completa; por defecto el de foto más reciente.

    Los valores que el juego oculta (secretos, sobre todo en combate) se descartan; el
    campo `redactados` de la foto dice cuántos. Nunca adivinarlos.
    """
    return bridge_get(f"/barbatos/snapshot{_query(section=section, character=character)}")


@mcp.tool
def fh_events(n: int = 30, character: str | None = None) -> dict[str, Any]:
    """
    Últimos n eventos del personaje (login, nivel, misión aceptada/entregada, zona,
    muerte; máx. 200) + estadísticas de la sesión actual (XP ganada, muertes, oro
    inicial, segundos por zona) y las últimas 5 sesiones.
    """
    return bridge_get(f"/barbatos/events{_query(n=max(1, min(int(n), 200)), character=character)}")


@mcp.tool(output_schema=None)  # devuelve contenido mixto (imagen + texto), no JSON estructurado
def fh_screenshot() -> list[Any]:
    """
    Pantallazo de SOLO la ventana de WoW (lo que se ve ahora mismo, JPEG ≤1600 px).
    Usarlo cuando la foto del archivo no basta (qué hay en pantalla, un tooltip, un
    mapa). Si `foreground` es false puede salir otra ventana encima.
    """
    res = bridge_post("/barbatos/screenshot", {})
    if not res.get("ok"):
        return [res]
    image = Image(data=base64.b64decode(res["image"]), format="jpeg")
    info = {k: v for k, v in res.items() if k != "image"}
    return [image, info]


@mcp.tool
def fh_send(title: str, text: str, notify: bool = True) -> dict[str, Any]:
    """
    Envía una respuesta al juego: la escribe en el buzón del addon (pestaña "Claude"
    de FeralHelper; el jugador la ve tras /reload). Con notify=True avisa al Pixel.

    IMPORTANTE: title y text deben ir en INGLÉS (el cliente y la interfaz del juego
    están en inglés). Texto plano, corto y útil; saltos de línea permitidos.
    title ≤ 80 caracteres, text ≤ 4000.
    """
    return bridge_post("/barbatos/send", {"title": title, "body": text, "notify": notify})
