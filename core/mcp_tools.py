"""
Argos Core - MCP tools.

Capa de herramientas expuesta a clientes MCP externos (Claude Desktop, ollmcp,
Flutter). Distinta de ARGOS_TOOLS (las del LangGraph interno). Cada tool se
registra contra la instancia `mcp` de core.mcp_server.

Las tools llaman a los backends por HTTP directo — no importan _Asmodeus.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from core.bridge_client import bridge_get, bridge_post
from core.mcp_server import mcp

# Colombia es UTC-5 fijo (sin DST). Evita depender de tzdata en el contenedor.
_COLOMBIA_TZ = timezone(timedelta(hours=-5))


@mcp.tool
def get_datetime() -> dict[str, Any]:
    """
    Devuelve la fecha y hora actuales reales del sistema en zona horaria de
    Colombia (UTC-5). Úsalo SIEMPRE para cualquier pregunta sobre la fecha,
    hora, día de la semana o "ahora" — los modelos de lenguaje no tienen reloj
    y alucinan fechas. No requiere red.
    """
    now = datetime.now(_COLOMBIA_TZ)
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    return {
        "iso": now.isoformat(),
        "fecha": now.strftime("%Y-%m-%d"),
        "hora": now.strftime("%H:%M:%S"),
        "dia_semana": dias[now.weekday()],
        "timezone": "America/Bogota (UTC-5)",
    }


def _stop_runner() -> None:
    """Detiene cualquier escena/sync activo. Idempotente — ok aunque no haya nada.

    Crítico: una escena (pulso, amanecer, screen-sync, tormenta...) reenvía
    comandos a los bombillos en bucle y PISA cualquier comando manual (off,
    color, brillo). Hay que pararla antes de un control manual o no 'pega'.
    """
    bridge_post("/amon/stop", {})


@mcp.tool
def amon_lights(
    action: Literal["on", "off", "brightness", "color", "scene", "stop", "status"],
    value: str | int | None = None,
    device_id: str = "all",
) -> dict[str, Any]:
    """
    Controla las luces Govee H6008 del hogar (subagente Amon) vía el Windows
    Bridge en la LAN. Sin nube.

    action:
      - "on" / "off"   : enciende / apaga (value ignorado)
      - "brightness"   : value = entero 1-100 (porcentaje)
      - "color"        : value = nombre o hex del color (ej "rojo", "#00ff00")
      - "scene"        : value = escena ("amanecer", "atardecer", "pulso", "tormenta")
      - "stop"         : detiene la escena/sync activo, deja las luces como están
      - "status"       : estado actual de cada bombillo (value ignorado)

    Nota: on/off/brightness/color detienen primero cualquier escena activa, si no
    la escena pisaría el comando y no surtiría efecto.

    device_id: "all" (default), o el id de un bombillo concreto.
    Devuelve {"ok": bool, ...}.
    """
    if action == "status":
        return bridge_get("/amon/status")

    if action == "stop":
        return bridge_post("/amon/stop", {})

    if action == "on":
        _stop_runner()
        return bridge_post("/amon/control", {"action": "turn_on", "device_id": device_id})

    if action == "off":
        _stop_runner()
        return bridge_post("/amon/control", {"action": "turn_off", "device_id": device_id})

    if action == "brightness":
        try:
            pct = max(1, min(100, int(value)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return {"ok": False, "error": "brightness requiere un entero 1-100 en 'value'"}
        _stop_runner()
        return bridge_post("/amon/control", {"action": "brightness", "device_id": device_id, "value": pct})

    if action == "color":
        if not value or not isinstance(value, str):
            return {"ok": False, "error": "color requiere el nombre/hex en 'value'"}
        _stop_runner()
        return bridge_post("/amon/control", {"action": "color", "device_id": device_id, "color": value.lower()})

    if action == "scene":
        if not value or not isinstance(value, str):
            return {"ok": False, "error": "scene requiere el nombre de la escena en 'value'"}
        scene = value.lower()
        # tormenta tiene su propio endpoint; las demás (amanecer/atardecer/pulso)
        # son escenas animadas del runner via /amon/scene {name}.
        if scene == "tormenta":
            return bridge_post("/amon/tormenta", {})
        return bridge_post("/amon/scene", {"name": scene})

    return {"ok": False, "error": f"acción no reconocida: {action}"}
