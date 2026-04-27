import asyncio
import logging

from fastapi import HTTPException

from app.core.config import settings
from app.utils.db import get_all_frozen_by_serial, freeze_port_db, unfreeze_port_db
from app.utils.fortigate_discovery import FortiGateDiscovery
from app.utils.fortiswitch_client import FortiSwitchClient

logger = logging.getLogger(__name__)


def get_campus_config(nom_campus: str) -> dict:
    campus_cfg = next((c for c in settings.campus if c["name"] == nom_campus), None)
    if not campus_cfg:
        raise HTTPException(status_code=404, detail="Campus no trobat.")
    return campus_cfg


def _build_fortigate_client(campus_cfg: dict) -> FortiGateDiscovery:
    return FortiGateDiscovery(
        fgt_ip=campus_cfg["fgt_ip"],
        api_key=campus_cfg["api_key"],
    )


def _format_fgt_error(exc: Exception) -> str:
    err = str(exc)
    if "403" in err:
        return "403: Acces denegat (Trusted Hosts)"
    return f"Error FGT: {err}"


async def _enrich_switch_status(sw: dict) -> dict:
    fsw = FortiSwitchClient(sw["ip"], settings.SWITCH_PASSWORD)
    version_acl = "Mai"

    try:
        if await fsw.login():
            version_acl = await fsw.obtenir_versio_segell()
    except Exception:
        logger.warning(
            "No s'ha pogut obtenir versio ACL del switch=%s ip=%s",
            sw.get("serial"),
            sw.get("ip"),
        )
        version_acl = "Error"
    finally:
        await fsw.close()

    sw.update(
        {
            "versio_acl": version_acl,
            "acls_sincronitzades": (version_acl == settings.current_version),
            "ports_congelats_count": len(await get_all_frozen_by_serial(sw["serial"])),
        }
    )
    return sw


async def list_campus_names() -> dict:
    logger.info("Llistat de campus consultat")
    return {"campus_disponibles": [c["name"] for c in settings.campus]}


async def list_switches_for_campus(nom_campus: str) -> dict:
    campus_cfg = get_campus_config(nom_campus)
    logger.info("Consulta de switches del campus=%s fgt=%s", nom_campus, campus_cfg["fgt_ip"])

    try:
        switches = await _build_fortigate_client(campus_cfg).llistar_switches()
        if not switches:
            raise RuntimeError("429 o error FGT")
    except Exception as exc:
        logger.exception("Error obtenint switches del campus=%s", nom_campus)
        raise HTTPException(status_code=502, detail=_format_fgt_error(exc))

    resultats = await asyncio.gather(*(_enrich_switch_status(sw) for sw in switches))
    logger.info("Campus=%s retornats %s switches", nom_campus, len(resultats))
    return {"campus": nom_campus, "switches": resultats, "fgt": campus_cfg["fgt_ip"]}


async def list_frozen_ports(serial: str):
    logger.info("Consulta de ports congelats del switch=%s", serial)
    return await get_all_frozen_by_serial(serial)


async def freeze_port(serial: str, port: int) -> dict:
    if await freeze_port_db(serial, port):
        logger.warning("Port congelat switch=%s port=%s", serial, port)
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="No s'ha pogut congelar el port")


async def unfreeze_port(serial: str, port: int) -> dict:
    if await unfreeze_port_db(serial, port):
        logger.warning("Port descongelat switch=%s port=%s", serial, port)
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="No s'ha pogut descongelar el port")
