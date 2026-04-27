import logging
import os
from pathlib import Path

import yaml


logger = logging.getLogger(__name__)


DEFAULT_CONFIG = {
    "settings": {
        "project_name": "FortiSwitch ACL Manager",
        "switch_user": "",
        "emergency_mode": False,
        "current_version": "2026.01.01.01",
        "switch_password": "",
    },
    "api_keys": {},
    "restrictions": {
        "forbidden_networks": [],
        "forbidden_models": ["S108FN", "S108FP"],
        "model_port_limits": {
            "108": 8,
            "248": 48,
            "424": 24,
            "448": 48,
            "DEFAULT_MAX": 48,
        },
    },
    "campus": [],
    "custom_services": [],
    "standard_acl_policy": [],
}


class Settings:
    def __init__(self, config_path: str | None = None, db_path: str | None = None):
        self.BASE_DIR = Path(__file__).resolve().parents[2]
        self.config_path = self._resolve_config_path(config_path)
        self.DB_PATH = self._resolve_db_path(db_path)
        self.LOG_DIR = self._resolve_log_dir()

        self.PROJECT_NAME = "FortiSwitch ACL Manager"
        self.SWITCH_USER = ""
        self.SWITCH_PASSWORD = ""
        self.current_version = "v0.0.0"
        self.is_ready = False
        self.config_error = None

        self.campus = []
        self.standard_acl_policy = []
        self.custom_services = []
        self.restrictions = {}

        self.load_all()

    def _resolve_config_path(self, config_path: str | None) -> Path:
        return Path(
            config_path
            or os.getenv("FORTI_API_CONFIG_PATH")
            or (self.BASE_DIR / "app" / "core" / "config.yaml")
        )

    def _resolve_db_path(self, db_path: str | None) -> Path:
        return Path(
            db_path
            or os.getenv("FORTI_API_DB_PATH")
            or (self.BASE_DIR / "fortiswitch.db")
        )

    def _resolve_log_dir(self) -> Path:
        return Path(
            os.getenv("FORTI_API_LOG_DIR")
            or (self.BASE_DIR / "logs")
        )

    def _read_config(self) -> dict:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _write_default_config(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                DEFAULT_CONFIG,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

    @staticmethod
    def _attach_api_keys(campus_list: list[dict], api_keys: dict) -> list[dict]:
        for campus_cfg in campus_list:
            campus_name = campus_cfg.get("name")
            if campus_name in api_keys:
                campus_cfg["api_key"] = api_keys[campus_name]
        return campus_list

    def load_all(self):
        """Carga la configuracion unificada desde un solo fichero."""
        self.is_ready = False
        self.config_error = None

        if not self.config_path.exists():
            self._write_default_config()
            logger.info("Configuracio inicial creada a %s", self.config_path)

        try:
            config = self._read_config()
            yaml_settings = config.get("settings", {})

            self.PROJECT_NAME = yaml_settings.get("project_name", self.PROJECT_NAME)
            self.current_version = yaml_settings.get("current_version", "2026.03.ERR")
            self.SWITCH_USER = yaml_settings.get("switch_user", self.SWITCH_USER)
            self.SWITCH_PASSWORD = yaml_settings.get("switch_password", "")

            self.restrictions = config.get("restrictions", {})
            self.campus = self._attach_api_keys(
                config.get("campus", []),
                config.get("api_keys", {}),
            )
            self.standard_acl_policy = config.get("standard_acl_policy", [])
            self.custom_services = config.get("custom_services", [])

            if self.campus:
                self.is_ready = True
                logger.info(
                    "Config carregada correctament. version=%s config=%s db=%s",
                    self.current_version,
                    self.config_path,
                    self.DB_PATH,
                )
            else:
                logger.warning(
                    "No s'ha trobat el bloc 'campus' al fitxer %s",
                    self.config_path,
                )
        except Exception as e:
            self.config_error = f"Error carregant config: {e}"
            logger.exception(self.config_error)

    def update_config(self, new_config_dict: dict) -> bool:
        """Actualiza config.yaml y recarga memoria."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    new_config_dict,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                )

            self.load_all()
            logger.info("Configuracio desada correctament a %s", self.config_path)
            return True
        except Exception as e:
            logger.exception("Error al desar la configuracio: %s", e)
            return False


settings = Settings()
