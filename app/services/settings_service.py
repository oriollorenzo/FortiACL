import logging
from datetime import datetime
from typing import Any

import yaml
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


def load_settings_from_yaml() -> dict[str, Any]:
    try:
        with open(settings.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        logger.info("Configuració carregada des de %s", settings.config_path)
        return data
    except Exception as e:
        logger.exception("Error carregant configuració")
        raise HTTPException(status_code=500, detail=str(e))


def save_settings_to_yaml(new_config: dict[str, Any]) -> dict[str, Any]:
    try:
        old_acls = getattr(settings, "standard_acl_policy", [])
        old_services = getattr(settings, "custom_services", [])
        old_restrictions = getattr(settings, "restrictions", {})

        new_acls = new_config.get("standard_acl_policy", [])
        new_services = new_config.get("custom_services", [])
        new_restrictions = new_config.get("restrictions", {})

        canvis_critics = (
            old_acls != new_acls
            or old_services != new_services
            or old_restrictions != new_restrictions
        )

        v_actual = getattr(settings, "current_version", "2026.01.01.01")

        if canvis_critics:
            avui = datetime.now().strftime("%Y.%m.%d")
            if v_actual and v_actual.startswith(avui):
                seq = int(v_actual.split(".")[-1]) + 1
                nova_v = f"{avui}.{seq:02d}"
            else:
                nova_v = f"{avui}.01"
            logger.info("Canvis crítics detectats. Nova versió=%s", nova_v)
        else:
            nova_v = v_actual
            logger.info("Sense canvis crítics. Es manté versió=%s", nova_v)

        if "settings" not in new_config:
            new_config["settings"] = {}

        new_config["settings"]["current_version"] = nova_v

        if settings.update_config(new_config):
            logger.info("Configuració desada correctament a %s", settings.config_path)
            return {"status": "success", "version": nova_v}

        raise RuntimeError("L'actualització del fitxer YAML ha fallat internament.")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error al desar la configuració")
        raise HTTPException(status_code=500, detail=str(e))
