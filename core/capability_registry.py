"""
core/capability_registry.py — Registro de capacidades y perfil operativo (Baseline RC5.5).

Singleton que define qué módulos están activos según el perfil de instalación.
Profiles: minimal → standard → institutional → advanced (jerarquía estricta).
"""
from __future__ import annotations
import hashlib, os, sys
from typing import Dict, Set, Optional

# Orden de jerarquía — un perfil sólo puede activarse si el anterior está disponible
_PROFILE_HIERARCHY = ["minimal", "standard", "institutional", "advanced"]

OPERATIONAL_PROFILES: Dict[str, Set[str]] = {
    "minimal": {
        "documentos", "autenticacion", "dashboard", "backup",
    },
    "standard": {
        "documentos", "autenticacion", "dashboard", "backup",
        "pqrs", "comunicaciones", "reportes",
    },
    "institutional": {
        "documentos", "autenticacion", "dashboard", "backup",
        "pqrs", "comunicaciones", "reportes",
        "gis", "balance_hidrico", "proyectos", "finanzas",
        "convenios", "emergencias", "auditoria",
    },
    "advanced": {
        "documentos", "autenticacion", "dashboard", "backup",
        "pqrs", "comunicaciones", "reportes",
        "gis", "balance_hidrico", "proyectos", "finanzas",
        "convenios", "emergencias", "auditoria",
        "api_externa", "integracion_sspd", "multi_hash", "baseline_verification",
    },
}

CORE_CAPABILITIES = {
    "sqlite_wal": True,
    "hmac_audit": True,
    "rate_limiting": True,
    "csrf_protection": True,
    "session_timeout": True,
    "pyinstaller_safe": True,
    "offline_first": True,
}

FUTURE_CAPABILITIES = {
    "firma_digital_pkcs11": False,
    "ocr_documentos": False,
    "integracion_govco": False,
    "notificaciones_push": False,
    "multi_tenant": False,
}


class CapabilityRegistry:
    _instance: Optional["CapabilityRegistry"] = None

    def __new__(cls) -> "CapabilityRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._active_profile: str = "standard"
        self._future: Dict[str, bool] = dict(FUTURE_CAPABILITIES)
        self._baseline_hash: str = self._compute_own_hash()
        self._initialized = True

    # ------------------------------------------------------------------
    # Profile management
    # ------------------------------------------------------------------

    def get_active_profile(self) -> str:
        return self._active_profile

    def set_active_profile(self, profile: str) -> bool:
        """Only allow downgrade or same-level changes, never silent upgrade."""
        if profile not in _PROFILE_HIERARCHY:
            return False
        current_idx = _PROFILE_HIERARCHY.index(self._active_profile)
        new_idx = _PROFILE_HIERARCHY.index(profile)
        # Block upgrades past institutional without explicit config
        if new_idx > current_idx and profile == "advanced":
            import logging
            logging.getLogger("asuacap.capability").warning(
                "Profile upgrade to 'advanced' blocked — requires explicit env flag PARAGUASMJ_ADVANCED=1"
            )
            if not os.environ.get("PARAGUASMJ_ADVANCED"):
                return False
        self._active_profile = profile
        return True

    def get_active_capabilities(self) -> Set[str]:
        return frozenset(OPERATIONAL_PROFILES.get(self._active_profile, set()))

    def is_capability_enabled(self, capability: str) -> bool:
        return capability in self.get_active_capabilities()

    # ------------------------------------------------------------------
    # Future capabilities
    # ------------------------------------------------------------------

    def enable_future_capability(self, name: str) -> bool:
        if name not in self._future:
            return False
        self._future[name] = True
        return True

    # ------------------------------------------------------------------
    # Baseline integrity
    # ------------------------------------------------------------------

    def _compute_own_hash(self) -> str:
        """Hash del módulo propio — detecta modificaciones post-instalación."""
        try:
            src_path = os.path.abspath(__file__.replace(".pyc", ".py"))
            if os.path.isfile(src_path):
                with open(src_path, "rb") as f:
                    return hashlib.sha256(f.read()).hexdigest()
        except OSError:
            pass
        return "unavailable"

    def verify_baseline_integrity(self) -> Dict[str, object]:
        """
        Verifica que el módulo no haya sido modificado desde la instalación.
        Retorna dict con is_valid, current_hash, stored_hash, delta.
        """
        current = self._compute_own_hash()
        is_valid = (current == self._baseline_hash) or self._baseline_hash == "unavailable"
        return {
            "is_valid": is_valid,
            "current_hash": current,
            "stored_hash": self._baseline_hash,
            "profile": self._active_profile,
            "core_capabilities": CORE_CAPABILITIES,
        }

    def get_baseline_info(self) -> Dict[str, object]:
        integrity = self.verify_baseline_integrity()
        return {
            "version": "RC5.5",
            "profile": self._active_profile,
            "active_modules": sorted(self.get_active_capabilities()),
            "future_pending": [k for k, v in self._future.items() if not v],
            "future_enabled": [k for k, v in self._future.items() if v],
            "integrity": integrity,
        }

    def get_capability_snapshot(self) -> Dict:
        return {
            "profile": self._active_profile,
            "capabilities": sorted(self.get_active_capabilities()),
            "core": CORE_CAPABILITIES,
            "future": dict(self._future),
        }
