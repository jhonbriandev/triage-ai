import json
import time
import logging
from django.conf import settings
from google import genai
from google.genai import types, errors

logger = logging.getLogger(__name__)


class ErrorGenerationAI(Exception):
    """Se lanza cuando no se pudo generar una sugerencia de IA, por cualquier motivo:
    falla de red, error de la API, respuesta que no es JSON válido, o JSON incompleto."""
    pass

PROMPT_BASE = """Eres un asistente de soporte técnico que ayuda a triar tickets.
Analiza el siguiente ticket y responde ÚNICAMENTE con un JSON (sin texto
adicional, sin markdown, sin explicaciones) con exactamente esta forma:

{{
  "suggestion_category": "una palabra o frase corta que describa el tipo de problema",
  "suggestion_priority": "baja, media, alta o urgente (elige una de estas 4 palabras exactas)",
  "generated_summary": "un resumen de 1 a 2 frases del problema, en español",
  "suggestion_answer": "una respuesta inicial breve y empática para el cliente, en español"
}}

Título del ticket: {title}
Descripción del ticket: {description}
"""
EXPECTED_FIELDS = {'suggestion_category', 'suggestion_priority', 'generated_summary', 'suggestion_answer'}
VALID_PRIORITY = {'baja', 'media', 'alta', 'urgente'}

def generate_suggestion_ai(ticket, max_tried = 3):
    """
    Llama a la API de Gemini con el título y la descripción del ticket, y
    devuelve un diccionario con las 4 claves que espera el modelo SugerenciaIA.

    Nunca deja escapar una excepción distinta a ErrorGeneracionIA — quien
    llama a esta función solo necesita saber "funcionó" o "no funcionó".
    
    Reintenta hasta max_intentos veces si Gemini responde 503
    (sobrecarga temporal). Otros errores no se reintentan, porque
    reintentar un JSON mal formado no lo va a arreglar.
    
    """
    prompt = PROMPT_BASE.format(title=ticket.title, description=ticket.description)
    for tried in range(max_tried):
        try:
            client = genai.Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(timeout=15000),  # 15 segundos, en milisegundos
            )
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                ),
            )
            break # si llegó aquí, sí funcionó — salimos del bucle de reintentos
        except errors.APIError as exc:
            is_temporal = getattr(exc, 'code', None) in (503, 429)
            # 503 = sobrecarga, 429 = demasiadas peticiones — ambos son "inténtalo después"

            if is_temporal and tried < max_tried - 1:
                wait = 2 ** tried  # 1er reintento: 1s, 2do: 2s, 3er: 4s
                logger.warning(
                    'Gemini saturado (intento %s/%s) para ticket #%s, reintentando en %ss',
                    tried + 1, max_tried, ticket.pk, wait,
                )
                time.sleep(wait)
                continue  # vuelve a intentar

            logger.warning('Gemini respondió con un error para el ticket #%s: %s', ticket.pk, exc)
            raise ErrorGenerationAI(f'La API de Gemini respondió con un error: {exc}') from exc
 
        except Exception as exc:
            logger.warning('Fallo inesperado llamando a Gemini para el ticket #%s: %s', ticket.pk, exc)
            raise ErrorGenerationAI(f'No se pudo contactar a la IA: {exc}') from exc

    try:
        data = json.loads(response.text)
    except (json.JSONDecodeError, TypeError, AttributeError):
        logger.warning(
            'La IA no devolvió JSON válido para el ticket #%s. Respuesta cruda: %r',
            ticket.pk, getattr(response, 'text', None),
        )
        raise ErrorGenerationAI('La IA no devolvió un JSON válido')

    missing = EXPECTED_FIELDS - data.keys()
    if missing:
        logger.warning('La IA omitió campos %s para el ticket #%s', missing, ticket.pk)
        raise ErrorGenerationAI(f'Faltan campos en la respuesta de la IA: {missing}')

    if data['suggestion_priority'] not in VALID_PRIORITY:
        logger.warning(
            'Prioridad sugerida inválida "%s" para el ticket #%s',
            data['suggestion_priority'], ticket.pk,
        )
        raise ErrorGenerationAI(f"Prioridad sugerida inválida: {data['suggestion_priority']!r}")

    return data
