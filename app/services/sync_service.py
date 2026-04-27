import asyncio
import ipaddress
import logging
import re

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.utils.db import get_all_frozen_by_serial
from app.utils.fortigate_discovery import FortiGateDiscovery
from app.utils.fortiswitch_client import FortiSwitchClient

logger = logging.getLogger(__name__)


def _get_campus_config(nom_campus: str) -> dict:
    campus_cfg = next((c for c in settings.campus if c["name"] == nom_campus), None)
    if not campus_cfg:
        raise HTTPException(status_code=404, detail="Campus no trobat")
    return campus_cfg


def _get_restrictions() -> dict:
    return getattr(settings, "restrictions", {})


def _is_forbidden_ip(ip_sw: str, forbidden_networks: list[str]) -> bool:
    for net in forbidden_networks:
        try:
            if ipaddress.ip_address(ip_sw) in ipaddress.ip_network(net):
                return True
        except ValueError:
            continue
    return False


def _is_forbidden_model(model_name: str, forbidden_models: list[str]) -> bool:
    return any(model in model_name for model in forbidden_models)


def _resolve_port_limit(model_name: str, limits_cfg: dict) -> int:
    limit = limits_cfg.get("DEFAULT_MAX", 48)
    sorted_keys = sorted(
        [k for k in limits_cfg.keys() if k != "DEFAULT_MAX"],
        key=lambda x: len(str(x)),
        reverse=True,
    )
    for key in sorted_keys:
        if str(key) in model_name:
            return limits_cfg[key]
    return limit


def _is_fs108_neighbor(device_name: str, device_serial: str) -> bool:
    candidate = f"{device_name} {device_serial}".upper()
    return "108" in candidate


def _summarize_results(resultats: list[dict], success_status: str) -> tuple[int, int, int]:
    ok = sum(1 for result in resultats if result["status"] == success_status)
    skipped = sum(1 for result in resultats if result["status"] == "skipped")
    errors = sum(1 for result in resultats if result["status"] == "error")
    return ok, skipped, errors


async def descarregar_mapa_ports_prohibits(
    fgt_ip: str,
    api_key: str,
    llista_monitor_switches: list,
) -> dict:
    cataleg_equips = {}
    for sw in llista_monitor_switches:
        nom_logic = sw.get("name")
        serial_fisic = sw.get("serial")
        if nom_logic and serial_fisic:
            cataleg_equips[nom_logic] = serial_fisic
            cataleg_equips[serial_fisic] = serial_fisic

    url = f"https://{fgt_ip}/api/v2/cmdb/switch-controller/managed-switch"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    params = {"vdom": "root"}
    mapa_prohibits = {}

    try:
        async with httpx.AsyncClient(
            verify=False,
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=30.0, pool=5.0),
        ) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code != 200:
                logger.error(
                    "Error HTTP %s descarregant CMDB de %s",
                    response.status_code,
                    fgt_ip,
                )
                return mapa_prohibits

            switches_cmdb = response.json().get("results", [])

            for sw in switches_cmdb:
                identificador_cmdb = sw.get("switch-id")
                ports_bloquejats = []

                for port in sw.get("ports", []):
                    nom_port = port.get("port-name")

                    if port.get("fortilink-port", 0) == 1:
                        ports_bloquejats.append(nom_port)
                        continue

                    vei_isl = port.get("isl-peer-device-name", "")
                    if vei_isl:
                        serial_vei = cataleg_equips.get(vei_isl, "")
                        if not _is_fs108_neighbor(vei_isl, serial_vei):
                            ports_bloquejats.append(nom_port)
                        continue

                    if port.get("type") == "trunk":
                        ports_bloquejats.append(nom_port)
                        membres = port.get("members", []) or port.get("member", [])
                        for membre in membres:
                            if isinstance(membre, dict):
                                nom_membre = (
                                    membre.get("port-name")
                                    or membre.get("name")
                                    or membre.get("member-name")
                                )
                            else:
                                nom_membre = membre

                            if nom_membre:
                                ports_bloquejats.append(nom_membre)

                if identificador_cmdb:
                    mapa_prohibits[identificador_cmdb] = ports_bloquejats
                    serial_propi = cataleg_equips.get(identificador_cmdb)
                    if serial_propi:
                        mapa_prohibits[serial_propi] = ports_bloquejats

    except Exception:
        logger.exception("Error de xarxa en obtenir mapa de ports prohibits")

    return mapa_prohibits


async def sync_batch_switches(serials: list[str], nom_campus: str) -> dict:
    campus_cfg = _get_campus_config(nom_campus)
    logger.info("SYNC START campus=%s serials_requested=%s", nom_campus, len(serials))

    fgt = FortiGateDiscovery(fgt_ip=campus_cfg["fgt_ip"], api_key=campus_cfg["api_key"])
    tots = await fgt.llistar_switches()
    seleccionats = [sw for sw in tots if sw["serial"] in serials]
    logger.info(
        "SYNC INVENTORY campus=%s discovered=%s selected=%s",
        nom_campus,
        len(tots),
        len(seleccionats),
    )

    mapa_seguretat_ports = await descarregar_mapa_ports_prohibits(
        campus_cfg["fgt_ip"],
        campus_cfg["api_key"],
        tots,
    )

    async def task_switch(sw_data: dict) -> dict:
        serial = sw_data["serial"]
        nom_logic = sw_data.get("name")
        ip_sw = sw_data.get("ip", "")
        model_name = sw_data.get("model_profile", "")
        restr = _get_restrictions()

        logger.info(
            "SYNC TOPOLOGY campus=%s protected_switch_entries=%s",
            nom_campus,
            len(mapa_seguretat_ports),
        )

        if _is_forbidden_ip(ip_sw, restr.get("forbidden_networks", [])):
            msg = f"IP {ip_sw} protegida"
            logger.warning(
                "SYNC SWITCH SKIPPED campus=%s serial=%s reason=%s",
                nom_campus,
                serial,
                msg,
            )
            return {"serial": serial, "status": "skipped", "msg": msg}

        if _is_forbidden_model(model_name, restr.get("forbidden_models", [])):
            msg = f"Model {model_name} exclòs"
            logger.warning(
                "SYNC SWITCH SKIPPED campus=%s serial=%s reason=%s",
                nom_campus,
                serial,
                msg,
            )
            return {"serial": serial, "status": "skipped", "msg": msg}

        if "108F" in model_name or "108" in model_name:
            msg = "Els models 108 no suporten ACLs prelookup"
            logger.warning(
                "SYNC SWITCH SKIPPED campus=%s serial=%s reason=%s",
                nom_campus,
                serial,
                msg,
            )
            return {"serial": serial, "status": "skipped", "msg": msg}

        ports_prohibits_fgt = mapa_seguretat_ports.get(nom_logic, [])
        if not ports_prohibits_fgt and serial not in mapa_seguretat_ports:
            msg = "No s'ha pogut verificar els ports de trunk/isl/fortilink"
            logger.error(
                "SYNC SWITCH ERROR campus=%s serial=%s reason=%s",
                nom_campus,
                serial,
                msg,
            )
            return {"serial": serial, "status": "error", "msg": msg}

        fsw = FortiSwitchClient(ip_sw, settings.SWITCH_PASSWORD)

        try:
            if not await fsw.login():
                msg = "Error de login. Revisa si adminsc esta donat d'alta"
                logger.error(
                    "SYNC SWITCH ERROR campus=%s serial=%s reason=%s",
                    nom_campus,
                    serial,
                    msg,
                )
                return {"serial": serial, "status": "error", "msg": msg}

            frozen_db = await get_all_frozen_by_serial(serial)
            ports_reals = await fsw.obtenir_ports_fisics()
            limits_cfg = restr.get("model_port_limits", {})
            limit = _resolve_port_limit(model_name, limits_cfg)

            ports_segurs = []
            ports_congelats_detectats = []

            for port in ports_reals:
                if port in ports_prohibits_fgt:
                    logger.debug(
                        "Saltant port %s del switch %s per proteccio topologica",
                        port,
                        serial,
                    )
                    continue

                match = re.search(r"(\d+)", str(port))
                if not match:
                    continue

                num = int(match.group(1))

                if num in frozen_db:
                    ports_congelats_detectats.append(str(port))
                    continue

                if 0 < num <= limit:
                    ports_segurs.append(port)

            logger.info(
                "SYNC SWITCH PORTS campus=%s serial=%s real_ports=%s frozen=%s protected=%s usable=%s model_limit=%s",
                nom_campus,
                serial,
                len(ports_reals),
                len(frozen_db),
                len(ports_prohibits_fgt),
                len(ports_segurs),
                limit,
            )

            if ports_congelats_detectats:
                logger.info(
                    "SYNC SWITCH FROZEN campus=%s serial=%s frozen_ports=%s",
                    nom_campus,
                    serial,
                    ",".join(ports_congelats_detectats),
                )

            if not ports_segurs:
                msg = "Sense ports d'acces valids"
                logger.warning(
                    "SYNC SWITCH SKIPPED campus=%s serial=%s reason=%s",
                    nom_campus,
                    serial,
                    msg,
                )
                return {"serial": serial, "status": "skipped", "msg": msg}

            logger.info(
                "SYNC SWITCH APPLY campus=%s serial=%s custom_services=%s acls_enabled=%s target_ports=%s",
                nom_campus,
                serial,
                len(settings.custom_services or []),
                len([p for p in getattr(settings, "standard_acl_policy", []) if p.get("enabled", True)]),
                len(ports_segurs),
            )

            await fsw.buidar_politiques_acl()
            await fsw.netejar_segells_antics()

            if settings.custom_services:
                for svc in settings.custom_services:
                    await fsw.eliminar_servei_si_existeix(svc["name"])
                await fsw.configurar_servicios_custom(settings.custom_services)

            politiques = [
                policy
                for policy in getattr(settings, "standard_acl_policy", [])
                if policy.get("enabled", True)
            ]

            await fsw.aplicar_acls_prelookup(
                serial=serial,
                lista_puertos=ports_segurs,
                standard_acls=politiques,
            )
            await fsw.crear_segell_sincro()

            logger.info(
                "SYNC SWITCH OK campus=%s serial=%s applied_ports=%s version=%s",
                nom_campus,
                serial,
                len(ports_segurs),
                getattr(settings, "current_version", "unknown"),
            )
            return {"serial": serial, "status": "success"}
        except Exception as e:
            logger.exception(
                "SYNC SWITCH ERROR campus=%s serial=%s reason=%s",
                nom_campus,
                serial,
                str(e),
            )
            return {"serial": serial, "status": "error", "msg": str(e)}
        finally:
            await fsw.close()

    resultats = await asyncio.gather(*(task_switch(sw) for sw in seleccionats), return_exceptions=True)
    ok, skipped, errors = _summarize_results(resultats, "success")
    logger.info(
        "SYNC END campus=%s total=%s ok=%s skipped=%s error=%s",
        nom_campus,
        len(resultats),
        ok,
        skipped,
        errors,
    )
    return {"results": resultats}


async def clear_batch_switches(serials: list[str], nom_campus: str) -> dict:
    campus_cfg = _get_campus_config(nom_campus)
    logger.warning("CLEAR START campus=%s serials_requested=%s", nom_campus, len(serials))

    fgt = FortiGateDiscovery(fgt_ip=campus_cfg["fgt_ip"], api_key=campus_cfg["api_key"])
    tots = await fgt.llistar_switches()
    seleccionats = [sw for sw in tots if sw["serial"] in serials]
    logger.info(
        "CLEAR INVENTORY campus=%s discovered=%s selected=%s",
        nom_campus,
        len(tots),
        len(seleccionats),
    )

    async def task_clear_only(sw_data: dict) -> dict:
        serial = sw_data["serial"]
        ip_sw = sw_data.get("ip", "")
        model_name = sw_data.get("model_profile", "")
        restr = _get_restrictions()

        logger.warning(
            "CLEAR SWITCH START campus=%s serial=%s ip=%s model=%s",
            nom_campus,
            serial,
            ip_sw,
            model_name,
        )

        if _is_forbidden_ip(ip_sw, restr.get("forbidden_networks", [])):
            msg = "IP Prohibida"
            logger.warning(
                "CLEAR SWITCH SKIPPED campus=%s serial=%s reason=%s",
                nom_campus,
                serial,
                msg,
            )
            return {"serial": serial, "status": "skipped", "msg": msg}

        if _is_forbidden_model(model_name, restr.get("forbidden_models", [])):
            msg = "Model a la llista de models protegits"
            logger.warning(
                "CLEAR SWITCH SKIPPED campus=%s serial=%s reason=%s",
                nom_campus,
                serial,
                msg,
            )
            return {"serial": serial, "status": "skipped", "msg": msg}

        fsw = FortiSwitchClient(ip_sw, settings.SWITCH_PASSWORD)
        try:
            if not await fsw.login():
                msg = "Login fail, revisa que adminsc estigui donat dalta"
                logger.error(
                    "CLEAR SWITCH ERROR campus=%s serial=%s reason=%s",
                    nom_campus,
                    serial,
                    msg,
                )
                return {"serial": serial, "status": "error", "msg": "Login fail"}

            await fsw.buidar_politiques_acl()
            await fsw.netejar_segells_antics()

            logger.warning("CLEAR SWITCH OK campus=%s serial=%s", nom_campus, serial)
            return {"serial": serial, "status": "cleared"}
        except Exception as e:
            logger.exception(
                "CLEAR SWITCH EXCEPTION campus=%s serial=%s",
                nom_campus,
                serial,
            )
            return {"serial": serial, "status": "error", "msg": str(e)}
        finally:
            await fsw.close()

    resultats = await asyncio.gather(*(task_clear_only(sw) for sw in seleccionats))
    cleared, skipped, errors = _summarize_results(resultats, "cleared")
    logger.warning(
        "CLEAR END campus=%s total=%s cleared=%s skipped=%s error=%s",
        nom_campus,
        len(resultats),
        cleared,
        skipped,
        errors,
    )
    return {"results": resultats}
