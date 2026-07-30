"""
core/calendario_colombiano.py — Calendario de dias habiles Colombia.
Festivos segun Ley 51/1983 (Ley Emiliani) y festivos fijos colombianos.
"""
from datetime import date, timedelta


# Festivos fijos (dia, mes)
_FESTIVOS_FIJOS = {
    (1, 1),   # Anio Nuevo
    (5, 1),   # Dia del Trabajo
    (7, 20),  # Independencia
    (8, 7),   # Batalla de Boyaca
    (12, 8),  # Inmaculada Concepcion
    (12, 25), # Navidad
}

# Festivos movibles (Ley Emiliani — se mueven al lunes siguiente)
_FESTIVOS_EMILIANI = {
    (1, 6),   # Reyes Magos
    (3, 19),  # San Jose
    (6, 29),  # San Pedro y San Pablo
    (8, 15),  # Asuncion de la Virgen
    (10, 12), # Dia de la Raza
    (11, 1),  # Todos los Santos
    (11, 11), # Independencia de Cartagena
}


def _siguiente_lunes(d):
    """Mueve la fecha al lunes siguiente si no es lunes."""
    dias = (7 - d.weekday()) % 7
    return d + timedelta(days=dias if dias else 7)


def festivos_anio(anio):
    """Retorna set de fechas festivas para el anio dado."""
    festivos = set()
    for mes, dia in _FESTIVOS_FIJOS:
        try:
            festivos.add(date(anio, mes, dia))
        except ValueError:
            pass
    for mes, dia in _FESTIVOS_EMILIANI:
        try:
            f = date(anio, mes, dia)
            if f.weekday() != 0:  # No es lunes
                f = _siguiente_lunes(f)
            festivos.add(f)
        except ValueError:
            pass
    # Semana Santa (Jueves y Viernes Santo) — se calcula a partir de Pascua
    pascua = _calcular_pascua(anio)
    festivos.add(pascua - timedelta(days=3))  # Jueves Santo
    festivos.add(pascua - timedelta(days=2))  # Viernes Santo
    # Festivos movibles post-Pascua (Ley Emiliani)
    for offset in (39, 60, 68):  # Ascension, Corpus Christi, Sagrado Corazon
        f = pascua + timedelta(days=offset)
        if f.weekday() != 0:
            f = _siguiente_lunes(f)
        festivos.add(f)
    return festivos


def _calcular_pascua(anio):
    """Algoritmo de Butcher para calcular la fecha de Pascua."""
    a = anio % 19
    b = anio // 100
    c = anio % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)


def calcular_fecha_habil(fecha_inicio, dias_habiles):
    """
    Calcula la fecha que resulta de sumar N dias habiles a fecha_inicio.
    Excluye sabados, domingos y festivos colombianos.
    """
    festivos = festivos_anio(fecha_inicio.year)
    if fecha_inicio.year != (fecha_inicio + timedelta(days=dias_habiles * 2)).year:
        festivos |= festivos_anio(fecha_inicio.year + 1)

    fecha = fecha_inicio
    habiles_contados = 0
    while habiles_contados < dias_habiles:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5 and fecha not in festivos:
            habiles_contados += 1
    return fecha


def dias_habiles_entre(fecha_ini, fecha_fin):
    """Cuenta dias habiles entre dos fechas."""
    festivos = festivos_anio(fecha_ini.year)
    if fecha_ini.year != fecha_fin.year:
        festivos |= festivos_anio(fecha_fin.year)
    count = 0
    f = fecha_ini
    while f < fecha_fin:
        f += timedelta(days=1)
        if f.weekday() < 5 and f not in festivos:
            count += 1
    return count
