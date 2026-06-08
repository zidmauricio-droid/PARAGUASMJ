"""
PARAGUASMJ - Baseline Congelada RC5.5
Nucleo institucional que NO debe modificarse sin autorizacion expresa.
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class BaselineController:
    """Controla la baseline congelada y las extensiones opcionales RC6.0."""

    # RC5.5 — COMPONENTES CONGELADOS
    FROZEN_COMPONENTS: Dict[str, Dict] = {
        "identity_hash":            {"version": "1.0", "locked": True},
        "chain_fingerprint":        {"version": "1.0", "locked": True},
        "epoch_registry":           {"version": "1.0", "locked": True},
        "merkle_registry":          {"version": "1.0", "locked": True},
        "verification_registry":    {"version": "1.0", "locked": True},
        "oais":                     {"version": "1.0", "locked": True},
        "worm":                     {"version": "1.0", "locked": True},
        "capability_registry":      {"version": "1.0", "locked": True},
        "baseline_lock":            {"version": "1.0", "locked": True},
        "architectural_constraints":{"version": "1.0", "locked": True},
    }

    # RC6.0 — EXTENSIONES OPCIONALES
    OPTIONAL_MODULES: Dict[str, Dict] = {
        "expedientes":          {"status": "experimental", "enabled": False, "requires_migration": True},
        "multi_tsa":            {"status": "planned",      "enabled": False},
        "blockchain":           {"status": "planned",      "enabled": False},
        "notary":               {"status": "planned",      "enabled": False},
        "hardware_trust":       {"status": "planned",      "enabled": False},
        "ocsp_crl":             {"status": "planned",      "enabled": False},
        "cryptographic_renewal":{"status": "planned",      "enabled": False},
        "self_verifying_aip":   {"status": "planned",      "enabled": False},
    }

    # GARANTIAS LEGALES — protegen el valor probatorio 10 años
    LEGACY_GUARANTEES: Dict[str, Any] = {
        "future_modules_are_optional": True,
        "absence_does_not_invalidate": [
            "evidentiary_value",
            "chain_of_custody",
            "integrity",
            "authenticity",
            "traceability",
            "oais_compliance",
        ],
    }

    # Archivos criticos cuyo hash se verifica
    _CRITICAL_FILES = [
        "app.py",
        "config.py",
        "core/capability_registry.py",
        "core/database_manager.py",
    ]

    def __init__(self, config_path: Path = Path("config/baseline.json")):
        self.config_path = config_path
        self._load_config()

    def _load_config(self) -> None:
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.FROZEN_COMPONENTS.update(cfg.get("frozen", {}))
                    self.OPTIONAL_MODULES.update(cfg.get("optional", {}))
            except (json.JSONDecodeError, OSError):
                pass

    def _file_sha256(self, rel_path: str) -> str:
        p = Path(rel_path)
        if not p.exists():
            return ""
        return hashlib.sha256(p.read_bytes()).hexdigest()

    def verify_integrity(self) -> bool:
        """Comprueba que los archivos criticos son legibles (existencia + hash no vacio)."""
        for f in self._CRITICAL_FILES:
            if not self._file_sha256(f):
                return False
        return True

    def can_modify(self, component: str, user: str) -> bool:
        """Solo el propietario del repositorio puede tocar componentes congelados."""
        if component in self.FROZEN_COMPONENTS and self.FROZEN_COMPONENTS[component].get("locked"):
            return user == "zidmauricio-droid"
        return True

    def enable_optional_module(self, module: str) -> Dict[str, Any]:
        """Activa un modulo RC6.0 si no requiere migracion, o retorna instrucciones."""
        if module not in self.OPTIONAL_MODULES:
            return {"error": f"Modulo '{module}' desconocido"}
        cfg = self.OPTIONAL_MODULES[module]
        if cfg.get("requires_migration"):
            idx = list(self.OPTIONAL_MODULES).index(module)
            return {
                "requires_migration": True,
                "migration_script": f"migrations/{idx + 13:03d}_{module}.sql",
                "enabled": False,
                "warning": "Modulo experimental — ejecutar migracion y pruebas antes de activar",
            }
        self.OPTIONAL_MODULES[module]["enabled"] = True
        return {"enabled": True, "module": module}

    def get_baseline_report(self) -> Dict[str, Any]:
        return {
            "rc_version":        "5.5",
            "baseline_id":       "PARAGUASMJ-RC5.5-20260607",
            "frozen":            list(self.FROZEN_COMPONENTS.keys()),
            "optional":          list(self.OPTIONAL_MODULES.keys()),
            "legacy_guarantees": self.LEGACY_GUARANTEES,
            "last_verified":     datetime.now().isoformat(),
            "integrity_ok":      self.verify_integrity(),
        }
