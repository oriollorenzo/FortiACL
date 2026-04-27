from datetime import datetime, timezone
import logging
import ipaddress

from fastapi import HTTPException

from app.core.config import settings
from app.utils.db import (
    insert_acl_counter_sample,
    list_acl_counter_samples_paginated,
    list_acl_counter_sample_campuses,
    delete_all_acl_counter_samples,
    delete_filtered_acl_counter_samples,
)
from app.utils.fortigate_discovery import FortiGateDiscovery
from app.utils.fortiswitch_client import FortiSwitchClient

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_switch_excluded(ip_sw: str, model_name: str) -> tuple[bool, str | None]:
    restr = getattr(settings, "restrictions", {}) or {}

    for net in restr.get("forbidden_networks", []):
        try:
            if ipaddress.ip_address(ip_sw) in ipaddress.ip_network(net):
                return True, f"IP {ip_sw} protegida"
        except ValueError:
            continue

    if any(m in (model_name or "") for m in restr.get("forbidden_models", [])):
        return True, f"Model {model_name} exclòs"

    if "108F" in (model_name or "") or "108" in (model_name or ""):
        return True, "Els models 108 no suporten ACLs prelookup"

    return False, None


def _get_acl_severity(acl_name: str) -> str:
    for acl in getattr(settings, "standard_acl_policy", []) or []:
        if acl.get("name") == acl_name:
            return (acl.get("severity") or "info").lower()
    return "info"


async def scan_acl_hits_for_campus(nom_campus: str, serials: list[str] | None = None) -> dict:
    c_cfg = next((c for c in settings.campus if c["name"] == nom_campus), None)
    if not c_cfg:
        raise HTTPException(status_code=404, detail="Campus no trobat")

    fgt = FortiGateDiscovery(fgt_ip=c_cfg["fgt_ip"], api_key=c_cfg["api_key"])
    switches = await fgt.llistar_switches()

    selected_serials = {s.strip() for s in (serials or []) if s and s.strip()}
    if selected_serials:
       switches = [sw for sw in switches if sw.get("serial") in selected_serials]

    logger.info("ACL HITS START campus=%s switches=%s", nom_campus, len(switches))

    results = []
    total_samples = 0

    for sw in switches:
        serial = sw["serial"]
        switch_name = sw.get("name", serial)
        ip_sw = sw.get("ip", "")
        model_name = sw.get("model_profile", "")

        excluded, reason = _is_switch_excluded(ip_sw, model_name)
        if excluded:
            logger.warning(
                "ACL HITS SWITCH SKIPPED campus=%s serial=%s reason=%s",
                nom_campus,
                serial,
                reason,
            )
            results.append({
                "serial": serial,
                "name": switch_name,
                "ip": ip_sw,
                "model": model_name,
                "status": "skipped",
                "msg": reason,
            })
            continue

        fsw = FortiSwitchClient(ip_sw, settings.SWITCH_PASSWORD)
        samples_for_switch = 0

        try:
            if not await fsw.login():
                logger.error(
                    "ACL HITS LOGIN FAIL campus=%s serial=%s",
                    nom_campus,
                    serial,
                )
                results.append({
                    "serial": serial,
                    "name": switch_name,
                    "status": "error",
                    "msg": "Login fail",
                })
                continue

            matches = await fsw.obtenir_acl_matches()

            logger.info(
                "ACL HITS SWITCH campus=%s serial=%s matches=%s",
                nom_campus,
                serial,
                len(matches),
            )

            for item in matches:
                policy_id = item["policy_id"]
                nom_acl = item["nom"]
                packets = int(item["packets"])

                acl_key = f"{policy_id}:{nom_acl}"
                severity = _get_acl_severity(nom_acl)

                await insert_acl_counter_sample(
                    campus=nom_campus,
                    serial=serial,
                    switch_name=switch_name,
                    acl_name=acl_key,
                    counter_value=packets,
                    severity=severity,
                )
                samples_for_switch += 1
                total_samples += 1

            results.append({
                "serial": serial,
                "name": switch_name,
                "status": "ok",
                "samples": samples_for_switch,
            })

        except Exception as e:
            logger.exception(
                "ACL HITS ERROR campus=%s serial=%s",
                nom_campus,
                serial,
            )
            results.append({
                "serial": serial,
                "name": switch_name,
                "status": "error",
                "msg": str(e),
            })
        finally:
            await fsw.close()

    logger.info(
        "ACL HITS END campus=%s switches=%s samples=%s",
        nom_campus,
        len(results),
        total_samples,
    )

    return {
        "campus": nom_campus,
        "switches": results,
        "samples_saved": total_samples,
        "scanned_at": _utc_now_iso(),
        "selected_serials": list(selected_serials) if selected_serials else [],
    }


async def get_acl_hit_samples_page(
    page: int = 1,
    per_page: int = 100,
    q: str = "",
    campus: str = "",
    severity: str = "",
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> dict:
    return await list_acl_counter_samples_paginated(
        page=page,
        per_page=per_page,
        q=q,
        campus=campus,
        severity=severity,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )

async def get_acl_hit_sample_campuses() -> list[str]:
    return await list_acl_counter_sample_campuses()


async def clear_acl_hit_samples() -> dict:
    deleted = await delete_all_acl_counter_samples()
    return {"deleted": deleted}


async def clear_filtered_acl_hit_samples(
    q: str = "",
    campus: str = "",
    severity: str = "",
) -> dict:
    deleted = await delete_filtered_acl_counter_samples(
        q=q,
        campus=campus,
        severity=severity,
    )
    return {"deleted": deleted}
