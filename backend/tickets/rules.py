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
        "caida total",
        "no funciona nada",
        "perdida de datos",
        "no puedo acceder",
        "bloqueado",
        "seguridad"
    ]

def has_critical_keywords(text):
    if text is None:
        return False
    text = normalize_text(text)

    for keyword in CRITICAL_KEYWORDS:
        keyword = normalize_text(keyword)

        if keyword in text:
            return True

    return False