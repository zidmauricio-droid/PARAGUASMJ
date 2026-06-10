/* SIGCA 2026 — JavaScript institucional
   Mejoras del PROGRAMA.doc:
   - Historial de navegación (pushState + popstate) 
   - Lazy loading de documentos
   - Cache frontend de datos frecuentes
*/

// ── Auto-cerrar alertas flash ────────────────────────────────────
document.addEventListener("DOMContentLoaded", function() {
  setTimeout(function() {
    document.querySelectorAll(".alert.alert-dismissible").forEach(function(el) {
      var a = bootstrap.Alert.getOrCreateInstance(el);
      if (a) a.close();
    });
  }, 5000);

  // Tooltips Bootstrap
  document.querySelectorAll("[data-bs-toggle='tooltip']").forEach(function(el) {
    new bootstrap.Tooltip(el);
  });

  // Confirmar acciones destructivas
  document.querySelectorAll("[data-confirm]").forEach(function(el) {
    el.addEventListener("click", function(e) {
      if (!confirm(el.getAttribute("data-confirm"))) e.preventDefault();
    });
  });

  // Badges de estado dinámicos
  document.querySelectorAll(".estado-badge[data-estado]").forEach(function(b) {
    b.classList.add("badge");
  });
});

// ── Historial de navegación (PROGRAMA.doc — Patrón Mediator) ────
// Permite usar los botones Atrás/Adelante del navegador
var _historialActivo = false;

function navegarA(panelId, itemId) {
  var state = { panel: panelId, itemId: itemId || null };
  var url   = "#" + panelId + (itemId ? "/" + itemId : "");
  history.pushState(state, "", url);
  _historialActivo = true;
}

window.addEventListener("popstate", function(event) {
  if (event.state && event.state.panel) {
    // Recargar la página en la ruta guardada si el SPA lo requiere
    var url = "/" + event.state.panel.replace(/_/g, "/");
    if (event.state.itemId) url += "/" + event.state.itemId;
    // Solo navegar si la URL real cambió
    if (window.location.pathname !== url) {
      window.location.href = url;
    }
  }
});

// ── Cache frontend (L1) para datos que no cambian seguido ────────
var _cache = {};
var _cacheTTL = {};

function cacheGet(key) {
  if (!_cache[key]) return null;
  if (Date.now() > _cacheTTL[key]) { delete _cache[key]; return null; }
  return _cache[key];
}

function cacheSet(key, data, ttlMs) {
  _cache[key]    = data;
  _cacheTTL[key] = Date.now() + (ttlMs || 60000); // 1 min por defecto
}

// ── Lazy loading de documentos (PROGRAMA.doc) ────────────────────
var _pagActual   = 1;
var _cargandoDocs= false;
var _hayMas      = true;

function cargarMasDocumentos(contenedorId, params) {
  if (_cargandoDocs || !_hayMas) return;
  _cargandoDocs = true;
  params = params || {};
  params.page = _pagActual;

  var qs = Object.entries(params).map(function(e) {
    return encodeURIComponent(e[0]) + "=" + encodeURIComponent(e[1]);
  }).join("&");

  fetch("/api/documentos?" + qs)
  .then(function(r){ return r.json(); })
  .then(function(data) {
    _cargandoDocs = false;
    _hayMas       = data.has_more;
    _pagActual++;
    var cont = document.getElementById(contenedorId);
    if (!cont) return;
    data.items.forEach(function(doc) {
      var tr = document.createElement("tr");
      tr.innerHTML = `
        <td><a href="/documentos/${doc.pk_registro_id}" class="fw-semibold text-primary text-decoration-none">${doc.codigo_completo}</a></td>
        <td class="text-truncate" style="max-width:220px;">${doc.asunto_resumen}</td>
        <td><small>${doc.fecha_radicacion}</small></td>
        <td><span class="badge estado-badge" data-estado="${doc.estado}">${doc.estado}</span></td>
      `;
      cont.appendChild(tr);
    });
    if (!_hayMas) {
      var msg = document.createElement("tr");
      msg.innerHTML = '<td colspan="4" class="text-center text-muted py-2" style="font-size:12px;">— Todos los documentos cargados —</td>';
      cont.appendChild(msg);
    }
  })
  .catch(function(e){ _cargandoDocs = false; console.error("Error cargando docs:", e); });
}

// ── KPIs en tiempo real (refresca cada 2 min) ────────────────────
function refrescarKPIs() {
  var kpisEls = document.querySelectorAll("[data-kpi]");
  if (!kpisEls.length) return;
  fetch("/api/dashboard/kpis")
  .then(function(r){ return r.json(); })
  .then(function(data) {
    kpisEls.forEach(function(el) {
      var k = el.getAttribute("data-kpi");
      if (data[k] !== undefined) el.textContent = data[k];
    });
  })
  .catch(function(){});
}
setInterval(refrescarKPIs, 120000);

// ── Formatear moneda COP ─────────────────────────────────────────
function formatearCOP(valor) {
  return "COP $" + Math.round(valor || 0).toLocaleString("es-CO");
}

// ── Confirmación antes de enviar formularios críticos ────────────
document.addEventListener("submit", function(e) {
  var form = e.target;
  var msg  = form.getAttribute("data-confirm");
  if (msg && !confirm(msg)) e.preventDefault();
});
