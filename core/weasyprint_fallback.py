"""
PARAGUASMJ - Motor de PDF con fallback automatico.
Prioridad: WeasyPrint (fidelidad CSS) → python-docx/HTML simple → ReportLab.
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional, Dict, Any


class PDFEngine:
    """Genera PDF usando el mejor motor disponible."""

    def __init__(self) -> None:
        self._wp  = self._check("weasyprint")
        self._rl  = self._check("reportlab")

    @staticmethod
    def _check(pkg: str) -> bool:
        try:
            __import__(pkg)
            return True
        except ImportError:
            return False

    @property
    def engine_name(self) -> str:
        if self._wp:
            return "WeasyPrint"
        if self._rl:
            return "ReportLab (contingencia)"
        return "Sin motor de PDF"

    def generate_pdf(
        self,
        html_content: str,
        output_path: Path,
        css_styles: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Genera PDF en output_path a partir de html_content.
        Retorna dict con claves: success, engine_used, output_path, error.
        """
        result: Dict[str, Any] = {
            "success": False,
            "engine_used": None,
            "output_path": str(output_path),
            "error": None,
        }

        # ── Motor 1: WeasyPrint ───────────────────────────────────────────
        if self._wp:
            try:
                from weasyprint import HTML, CSS  # type: ignore
                stylesheets = [CSS(string=css_styles)] if css_styles else None
                HTML(string=html_content).write_pdf(str(output_path), stylesheets=stylesheets)
                result.update(success=True, engine_used="WeasyPrint (alta fidelidad)")
                return result
            except Exception as exc:
                result["error"] = f"WeasyPrint: {exc}"

        # ── Motor 2: ReportLab (fallback offline) ─────────────────────────
        if self._rl:
            try:
                from reportlab.pdfgen import canvas   # type: ignore
                from reportlab.lib.pagesizes import letter
                text = re.sub(r"<[^>]+>", " ", html_content)
                text = re.sub(r"\s+", " ", text).strip()
                c = canvas.Canvas(str(output_path), pagesize=letter)
                c.setFont("Helvetica-Bold", 14)
                c.drawString(72, 750, "PARAGUASMJ - Documento Institucional")
                c.setFont("Helvetica", 10)
                c.drawString(72, 730, "(Generado en modo contingencia offline - ReportLab)")
                y = 700
                for line in (text[i : i + 90] for i in range(0, min(len(text), 3600), 90)):
                    c.drawString(72, y, line)
                    y -= 14
                    if y < 72:
                        c.showPage()
                        y = 750
                c.save()
                result.update(success=True, engine_used="ReportLab (modo contingencia)")
                return result
            except Exception as exc:
                prev = result.get("error") or ""
                result["error"] = f"{prev} | ReportLab: {exc}".lstrip(" | ")

        result["error"] = (result.get("error") or "") + " | Sin motor PDF instalado"
        return result


# Instancia global — importar desde otros modulos con:
#   from core.weasyprint_fallback import pdf_engine
pdf_engine = PDFEngine()
