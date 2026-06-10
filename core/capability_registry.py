"""
core/capability_registry.py — Registro de capacidades y perfil operativo.

# ============================================================
# PARAGUASMJ BASELINE RC5.5
#
# Esta version constituye la linea base institucional.
#
# Los modulos RC6.0:
# - NO son obligatorios
# - NO forman parte de la cadena probatoria principal
# - NO afectan identidad documental
# - NO afectan OAIS
# - NO afectan WORM
# - NO afectan Verification Registry
#
# Pueden incorporarse mediante actualizacion futura.
#
# Baseline ID:
# PARAGUASMJ-RC5.5-20260607
# ============================================================

Tres capas arquitectonicas:
  CAPA 1 — Nucleo Congelado: UUID, hashes, OAIS, WORM. Nunca modificar.
  CAPA 2 — Modulos Operativos: expedientes, reportes, etc. Actualizables.
  CAPA 3 — Extensiones RC6.0: deshabilitadas hasta aprobacion formal.

Singleton: una sola instancia por proceso.
"""
from __future__ import annotations
import hashlib, os
from typing import Dict, Set, Optional

BASELINE_ID      = "PARAGUASMJ-RC5.5-20260607"
BASELINE_VERSION = "RC5.5"

_PROFILE_HIERARCHY = ["minimal", "standard", "institutional", "advanced"]

# ── Capa 2: Modulos Operativos por perfil ────────────────────────────────────
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
        "convenios", "emergencias", "auditoria", "expedientes",
    },
    "advanced": {
        "documentos", "autenticacion", "dashboard", "backup",
        "pqrs", "comunicaciones", "reportes",
        "gis", "balance_hidrico", "proyectos", "finanzas",
        "convenios", "emergencias", "auditoria", "expedientes",
        "api_externa", "integracion_sspd", "multi_hash", "baseline_verification",
    },
}

# ── Capa 1: Capacidades del nucleo congelado ─────────────────────────────────
CORE_CAPABILITIES = {
    "sqlite_wal":        True,
    "hmac_audit":        True,
    "rate_limiting":     True,
    "csrf_protection":   True,
    "session_timeout":   True,
    "pyinstaller_safe":  True,
    "offline_first":     True,
    "multi_hash_sha256": True,
    "multi_hash_sha3":   True,
    "multi_hash_blake2": True,
}

# ── Capa 3: Extensiones RC6.0 (todas deshabilitadas) ─────────────────────────
RC6_EXTENSIONS: Dict[str, bool] = {
    "multi_tsa":               False,
    "blockchain_anchor":       False,
    "notary_anchor":           False,
    "hardware_trust":          False,
    "ocsp_crl_preservation":   False,
    "cryptographic_renewal":   False,
    "self_verifying_aip":      False,
}

# Capacidades futuras Capa 2 (pendientes de desarrollo)
FUTURE_CAPABILITIES: Dict[str, bool] = {
    "firma_digital_pkcs11": False,
    "ocr_documentos":       False,
    "integracion_govco":    False,
    "notificaciones_push":  False,
    "multi_tenant":         False,
}


class CapabilityRegistry:
    """Singleton — una instancia por proceso."""

    _instance: Optional["CapabilityRegistry"] = None

    def __new__(cls) -> "CapabilityRegistry":
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._initialized = False
            cls._instance = inst
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._active_profile: str = "standard"
        self._future: Dict[str, bool]     = dict(FUTURE_CAPABILITIES)
        self._rc6:    Dict[str, bool]     = dict(RC6_EXTENSIONS)
        self._baseline_hash: str          = self._compute_own_hash()
        self._initialized = True

    # ── Perfil ───────────────────────────────────────────────────────────────

    def get_active_profile(self) -> str:
        return self._active_profile

    def set_active_profile(self, profile: str) -> bool:
        if profile not in _PROFILE_HIERARCHY:
            return False
        current_idx = _PROFILE_HIERARCHY.index(self._active_profile)
        new_idx     = _PROFILE_HIERARCHY.index(profile)
        if new_idx > current_idx and profile == "advanced":
            import logging
            logging.getLogger("sigca.capability").warning(
                "Upgrade a 'advanced' bloqueado — requiere env PARAGUASMJ_ADVANCED=1"
            )
            if not os.environ.get("PARAGUASMJ_ADVANCED"):
                return False
        self._active_profile = profile
        return True

    def get_active_capabilities(self) -> frozenset:
        return frozenset(OPERATIONAL_PROFILES.get(self._active_profile, set()))

    def is_capability_enabled(self, capability: str) -> bool:
        return capability in self.get_active_capabilities()

    # ── Extensiones RC6.0 (Capa 3) ────────────────────────────────────────────

    def is_rc6_enabled(self, extension: str) -> bool:
        """Siempre False hasta aprobacion formal — cumple politica de activacion."""
        return self._rc6.get(extension, False)

    def enable_rc6_extension(self, name: str, approval_token: str) -> bool:
        """
        Activa una extension RC6.0. Requiere token de aprobacion institucional.
        No modifica UUID, identity_hash, chain_fingerprint, epoch_registry, OAIS ni WORM.
        """
        if name not in self._rc6:
            return False
        if not approval_token or len(approval_token) < 16:
            import logging
            logging.getLogger("sigca.capability").error(
                f"RC6 extension '{name}' requiere token de aprobacion institucional"
            )
            return False
        self._rc6[name] = True
        return True

    # ── Capacidades futuras (Capa 2 pendientes) ───────────────────────────────

    def enable_future_capability(self, name: str) -> bool:
        if name not in self._future:
            return False
        self._future[name] = True
        return True

    # ── Integridad del baseline ───────────────────────────────────────────────

    def _compute_own_hash(self) -> str:
        try:
            src = os.path.abspath(__file__.replace(".pyc", ".py"))
            if os.path.isfile(src):
                with open(src, "rb") as f:
                    return hashlib.sha256(f.read()).hexdigest()
        except OSError:
            pass
        return "unavailable"

    def verify_baseline_integrity(self) -> Dict[str, object]:
        current  = self._compute_own_hash()
        is_valid = (current == self._baseline_hash) or self._baseline_hash == "unavailable"
        return {
            "is_valid":        is_valid,
            "current_hash":    current,
            "stored_hash":     self._baseline_hash,
            "baseline_id":     BASELINE_ID,
            "profile":         self._active_profile,
            "core_capabilities": CORE_CAPABILITIES,
        }

    # ── Metadata de documento (para almacenar en registro_central) ────────────

    def get_document_metadata(self) -> Dict[str, object]:
        """
        JSON que debe guardarse en cada documento para trazabilidad arquitectonica.
        Permite verificar en 5/10/20 anios que capacidades estaban activas.
        """
        return {
            "baseline_id":        BASELINE_ID,
            "core_version":       BASELINE_VERSION,
            "extensions_enabled": [k for k, v in self._rc6.items() if v],
        }

    # ── Info completa ─────────────────────────────────────────────────────────

    def get_baseline_info(self) -> Dict[str, object]:
        return {
            "baseline_id":      BASELINE_ID,
            "version":          BASELINE_VERSION,
            "profile":          self._active_profile,
            "active_modules":   sorted(self.get_active_capabilities()),
            "future_pending":   [k for k, v in self._future.items() if not v],
            "future_enabled":   [k for k, v in self._future.items() if v],
            "rc6_pending":      [k for k, v in self._rc6.items() if not v],
            "rc6_enabled":      [k for k, v in self._rc6.items() if v],
            "integrity":        self.verify_baseline_integrity(),
        }

    def get_capability_snapshot(self) -> Dict:
        return {
            "baseline_id": BASELINE_ID,
            "profile":     self._active_profile,
            "layer_1":     CORE_CAPABILITIES,
            "layer_2":     sorted(self.get_active_capabilities()),
            "layer_3":     dict(self._rc6),
        }
