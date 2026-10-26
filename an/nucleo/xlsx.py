"""Salidas xlsx: texto que viene de datos (nombres, etiquetas) nunca se vuelve fórmula."""


def poner_texto(celda, valor):
    """Asigna `valor`; si es texto que Excel leería como fórmula (`= + - @`), la celda queda de tipo texto."""
    celda.value = valor
    if isinstance(valor, str) and valor[:1] in ("=", "+", "-", "@"):
        celda.data_type = "s"
    return celda
