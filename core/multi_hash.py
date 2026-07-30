"""
core/multi_hash.py — Hashing multi-algoritmo para documentos (Baseline RC5.5).

SHA-256 (NIST), SHA3-256 (Keccak), BLAKE2b (speed+security) en paralelo.
Ninguno depende de los demás — si un algoritmo se rompe en 10 años,
los otros dos siguen siendo válidos.
"""
from __future__ import annotations
import hashlib
from typing import Dict, Union


class MultiHash:
    """Genera y verifica hashes múltiples de contenido arbitrario."""

    ALGORITHMS = ("sha256", "sha3_256", "blake2b")

    @classmethod
    def generate(cls, content: Union[bytes, str]) -> Dict[str, str]:
        """
        Genera los tres hashes del contenido.
        Retorna dict con claves sha256, sha3_256, blake2b.
        """
        if isinstance(content, str):
            content = content.encode("utf-8")
        return {
            "sha256":   hashlib.sha256(content).hexdigest(),
            "sha3_256": hashlib.sha3_256(content).hexdigest(),
            "blake2b":  hashlib.blake2b(content, digest_size=32).hexdigest(),
        }

    @classmethod
    def verify(cls, content: Union[bytes, str], stored: Dict[str, str]) -> Dict[str, bool]:
        """
        Verifica el contenido contra los hashes almacenados.
        Retorna dict por algoritmo: True = coincide, False = fallo.
        Algoritmos ausentes en stored se reportan como None (no verificado).
        """
        if isinstance(content, str):
            content = content.encode("utf-8")
        current = cls.generate(content)
        return {
            alg: (current[alg] == stored[alg]) if alg in stored else None
            for alg in cls.ALGORITHMS
        }

    @classmethod
    def is_fully_valid(cls, content: Union[bytes, str], stored: Dict[str, str]) -> bool:
        """True sólo si TODOS los algoritmos presentes en stored coinciden."""
        results = cls.verify(content, stored)
        return all(v is True for v in results.values() if v is not None)

    @classmethod
    def consensus(cls, results: Dict[str, bool]) -> str:
        """
        Retorna 'valid', 'partial', 'invalid' o 'unknown'.
        'partial' = al menos uno válido pero no todos — señal de alerta.
        """
        values = [v for v in results.values() if v is not None]
        if not values:
            return "unknown"
        if all(values):
            return "valid"
        if any(values):
            return "partial"
        return "invalid"


class DocumentMultiHash:
    """Wrapper orientado a documentos almacenados en la BD."""

    @staticmethod
    def from_file_bytes(data: bytes) -> Dict[str, str]:
        return MultiHash.generate(data)

    @staticmethod
    def from_text(text: str) -> Dict[str, str]:
        return MultiHash.generate(text.encode("utf-8"))

    @staticmethod
    def verify_document(data: bytes, stored_hashes: Dict[str, str]) -> Dict:
        results = MultiHash.verify(data, stored_hashes)
        return {
            "per_algorithm": results,
            "consensus": MultiHash.consensus(results),
            "is_valid": MultiHash.is_fully_valid(data, stored_hashes),
        }
