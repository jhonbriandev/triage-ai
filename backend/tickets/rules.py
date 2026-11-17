import re

def normalize_text(text):
    text = text.lower()
    text = text.replace("á", "a")
    text = text.replace("é", "e")
    text = text.replace("í", "i")
    text = text.replace("ó", "o")
    text = text.replace("ú", "u")
    text = text.replace(",", "")
    text = text.replace(".", "")
    return text


CRITICAL_KEYWORDS = [
    # Caída total: excluye negaciones
    r'(?<!no hay )(?<!no hay una )(?<!no existe )(?<!no hubo )\bcaida\s+total\b',

    # Expresión crítica completa
    r"\bno\s+funciona\s+nada\b",

    # Pérdida de datos: excluye negaciones
    r"(?<!no hay )(?<!no existe )(?<!no hubo )(?<!sin )\bperdida\s+de\s+datos\b",

    # Expresión crítica completa
    r"\bno\s+puedo\s+acceder\b",

    # Bloqueado: excluye prefijos y negaciones
    r"(?<!des)\b(?<!no esta )(?<!no se )(?<!no )bloquead[oa]s?\b",

    # Seguridad
    r"\bseguridad\b"
]


def has_critical_keywords(text):
    if text is None:
        return False

    text = normalize_text(text)

    # print(f"TEXT NORMALIZED: {repr(text)}")

    for keyword in CRITICAL_KEYWORDS:
        if re.search(keyword, text):
            # print(f"CRITICAL MATCH: {keyword}")
            return True

    return False