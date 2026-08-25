import json
import logging
from django.conf import settings
from google import genai
from google.genai import types, errors

logger = logging.getLogger(__name__)


class ErrorGenerationIA(Exception):
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

def generate_suggestion_ia(ticket):
    """
    Llama a la API de Gemini con el título y la descripción del ticket, y
    devuelve un diccionario con las 4 claves que espera el modelo SugerenciaIA.

    Nunca deja escapar una excepción distinta a ErrorGeneracionIA — quien
    llama a esta función solo necesita saber "funcionó" o "no funcionó".
    """
    prompt = PROMPT_BASE.format(title=ticket.title, description=ticket.description)

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
    except errors.APIError as exc:
        logger.warning('Gemini respondió con un error para el ticket #%s: %s', ticket.pk, exc)
        raise ErrorGenerationIA(f'La API de Gemini respondió con un error: {exc}') from exc
    except Exception as exc:
        logger.warning('Fallo inesperado llamando a Gemini para el ticket #%s: %s', ticket.pk, exc)
        raise ErrorGenerationIA(f'No se pudo contactar a la IA: {exc}') from exc

    try:
        data = json.loads(response.text)
    except (json.JSONDecodeError, TypeError, AttributeError):
        logger.warning(
            'La IA no devolvió JSON válido para el ticket #%s. Respuesta cruda: %r',
            ticket.pk, getattr(response, 'text', None),
        )
        raise ErrorGenerationIA('La IA no devolvió un JSON válido')

    missing = EXPECTED_FIELDS - data.keys()
    if missing:
        logger.warning('La IA omitió campos %s para el ticket #%s', missing, ticket.pk)
        raise ErrorGenerationIA(f'Faltan campos en la respuesta de la IA: {missing}')

    if data['suggestion_priority'] not in VALID_PRIORITY:
        logger.warning(
            'Prioridad sugerida inválida "%s" para el ticket #%s',
            data['suggestion_priority'], ticket.pk,
        )
        raise ErrorGenerationIA(f"Prioridad sugerida inválida: {data['suggestion_priority']!r}")

    return data
