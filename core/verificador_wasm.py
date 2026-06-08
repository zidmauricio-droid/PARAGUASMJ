"""
core/verificador_wasm.py — Genera verificador HTML autónomo para documentos.

El HTML resultante es standalone (sin dependencias externas) y usa
crypto.subtle para SHA-256. SHA-3 y BLAKE2b NO están disponibles en
la Web Crypto API nativa — el verificador lo indica explícitamente
en lugar de hacer una aproximación silenciosa que daría falsos positivos.
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict


def generar_verificador_html(doc_info: Dict[str, str]) -> str:
    """
    Genera HTML standalone con verificador criptográfico.

    doc_info debe incluir:
      - titulo, codigo, fecha_creacion
      - hash_sha256, hash_sha3_256 (opcional), hash_blake2b (opcional)
    """
    titulo        = doc_info.get("titulo", "Documento")
    codigo        = doc_info.get("codigo", "")
    fecha         = doc_info.get("fecha_creacion", datetime.now().strftime("%Y-%m-%d"))
    hash_sha256   = doc_info.get("hash_sha256", "")
    hash_sha3     = doc_info.get("hash_sha3_256", "")
    hash_blake2b  = doc_info.get("hash_blake2b", "")
    generado_en   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sha3_display   = hash_sha3   if hash_sha3   else "(no registrado)"
    blake2b_display = hash_blake2b if hash_blake2b else "(no registrado)"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Verificador — {titulo}</title>
<style>
  body{{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto;padding:1rem;color:#222}}
  h1{{font-size:1.3rem;color:#1E3A8A}}
  .hash{{font-family:monospace;font-size:.78rem;word-break:break-all;background:#f4f4f4;padding:.4rem;border-radius:4px;margin:.3rem 0}}
  .ok{{color:#16a34a;font-weight:600}} .fail{{color:#dc2626;font-weight:600}}
  .warn{{color:#d97706;font-size:.85rem;margin-top:.5rem}}
  #drop{{border:2px dashed #94a3b8;border-radius:8px;padding:2rem;text-align:center;cursor:pointer;margin:1.5rem 0}}
  #drop:hover{{background:#f0f9ff}} #resultado{{margin-top:1rem}}
  table{{width:100%;border-collapse:collapse;font-size:.85rem}}
  td,th{{padding:.4rem .6rem;border:1px solid #e2e8f0;text-align:left}}
  th{{background:#f8fafc}}
</style>
</head>
<body>
<h1>Verificador de Autenticidad — PARAGUASMJ</h1>
<table>
  <tr><th>Campo</th><th>Valor</th></tr>
  <tr><td>Título</td><td>{titulo}</td></tr>
  <tr><td>Código</td><td>{codigo}</td></tr>
  <tr><td>Fecha creación</td><td>{fecha}</td></tr>
  <tr><td>Verificador generado</td><td>{generado_en}</td></tr>
</table>

<h2 style="font-size:1rem;margin-top:1.5rem">Hashes de referencia</h2>
<table>
  <tr><th>Algoritmo</th><th>Hash esperado</th><th>Verificable aquí</th></tr>
  <tr>
    <td>SHA-256</td>
    <td><span class="hash">{hash_sha256}</span></td>
    <td>✅ Sí (Web Crypto API)</td>
  </tr>
  <tr>
    <td>SHA3-256</td>
    <td><span class="hash">{hash_sha3}</span></td>
    <td>⚠️ Manual (ver abajo)</td>
  </tr>
  <tr>
    <td>BLAKE2b-256</td>
    <td><span class="hash">{hash_blake2b}</span></td>
    <td>⚠️ Manual (ver abajo)</td>
  </tr>
</table>

<div class="warn">
  ⚠️ Los navegadores no implementan SHA-3 ni BLAKE2b de forma nativa.
  Este verificador calcula SHA-256 en el navegador. Para verificar SHA-3 y BLAKE2b
  use: <code>python -c "import hashlib; d=open('archivo','rb').read();
  print(hashlib.sha3_256(d).hexdigest())"</code>
</div>

<div id="drop" ondragover="event.preventDefault()" ondrop="manejarDrop(event)">
  <p>Arrastre el archivo aquí para verificar SHA-256</p>
  <input type="file" id="fileInput" style="display:none" onchange="manejarArchivo(this.files[0])">
  <button onclick="document.getElementById('fileInput').click()" style="margin-top:.5rem;padding:.4rem 1rem">
    Seleccionar archivo
  </button>
</div>
<div id="resultado"></div>

<script>
const HASH_SHA256_ESPERADO = "{hash_sha256}";

function manejarDrop(e) {{
  e.preventDefault();
  const f = e.dataTransfer.files[0];
  if (f) manejarArchivo(f);
}}

async function manejarArchivo(file) {{
  const div = document.getElementById("resultado");
  div.innerHTML = "<p>Calculando...</p>";
  try {{
    const buf = await file.arrayBuffer();
    const hashBuf = await crypto.subtle.digest("SHA-256", buf);
    const hashHex = Array.from(new Uint8Array(hashBuf))
      .map(b => b.toString(16).padStart(2, "0")).join("");

    const ok = hashHex === HASH_SHA256_ESPERADO;
    div.innerHTML = `
      <p><strong>Archivo:</strong> ${{file.name}} (${{(file.size/1024).toFixed(1)}} KB)</p>
      <p><strong>SHA-256 calculado:</strong></p>
      <div class="hash">${{hashHex}}</div>
      <p class="${{ok ? "ok" : "fail"}}">${{ok ? "✅ SHA-256 VERIFICADO — el archivo es auténtico" : "❌ SHA-256 NO COINCIDE — el archivo fue modificado o es incorrecto"}}</p>
      ${{!ok ? '<p class="warn">Si SHA-256 falla, el documento no es el original independientemente de los otros algoritmos.</p>' : ""}}
    `;
  }} catch(err) {{
    div.innerHTML = `<p class="fail">Error al procesar el archivo: ${{err.message}}</p>`;
  }}
}}
</script>
</body>
</html>"""
