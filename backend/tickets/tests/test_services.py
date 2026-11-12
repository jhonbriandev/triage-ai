
import pytest
import json

from unittest.mock import patch, MagicMock

from tickets.services import (
    generate_suggestion_ai,
    ErrorGenerationAI,
)
from tickets.tests.factories import TicketFactory


def response_mock(text):
    # Creamos una respuesta falsa que imita la respuesta de Gemini.
    # MagicMock permite simular objetos y métodos sin utilizar la API real.
    response = MagicMock()
    response.text = text

    return response


@pytest.mark.django_db
class TestGenerateSuggestionAI:

    def test_happy_path_returns_four_keys(self):
        ticket = TicketFactory()

        # Definimos el JSON válido que esperamos recibir de Gemini.
        mock_suggestion = {
            "suggestion_category": "Bug",
            "suggestion_priority": "alta",
            "generated_summary": "Resumen del problema",
            "suggestion_answer": "Revisar la conexión del servicio."
        }

        with patch('tickets.services.genai.Client') as mock_client:

            # Simulamos que Gemini devuelve nuestro JSON.
            mock_client.return_value.models.generate_content.return_value = (
                response_mock(json.dumps(mock_suggestion))
            )

            results = generate_suggestion_ai(ticket)

        # Comprobamos que el servicio devuelve las cuatro claves esperadas.
        assert set(results.keys()) == set(mock_suggestion.keys())

        # Comprobamos que los valores procesados coinciden con el JSON.
        assert results == mock_suggestion

    def test_api_error_raises_error_generation_ai(self):
        ticket = TicketFactory()

        # Simulamos un fallo de conexión o un error de la API de Gemini.
        with patch('tickets.services.genai.Client') as mock_client:

            mock_client.return_value.models.generate_content.side_effect = (
                Exception('Network error')
            )

            # Comprobamos que el servicio transforma el error
            # en nuestra excepción personalizada.
            with pytest.raises(ErrorGenerationAI):
                generate_suggestion_ai(ticket)

    def test_invalid_json_raises_error_generation_ai(self):
        ticket = TicketFactory()

        # Simulamos una respuesta que no cumple el formato JSON.
        invalid_output = 'This is not valid JSON'

        with patch('tickets.services.genai.Client') as mock_client:

            mock_client.return_value.models.generate_content.return_value = (
                response_mock(invalid_output)
            )

            # El servicio debe detectar el JSON inválido
            # y lanzar nuestra excepción personalizada.
            with pytest.raises(ErrorGenerationAI):
                generate_suggestion_ai(ticket)

    def test_invalid_priority_raises_error_generation_ai(self):
        ticket = TicketFactory()

        # El JSON es válido, pero contiene una prioridad no permitida.
        mock_suggestion = {
            "suggestion_category": "Bug",
            "suggestion_priority": "SUPER URGENTE",
            "generated_summary": "Resumen del problema",
            "suggestion_answer": "Revisar el sistema."
        }

        with patch('tickets.services.genai.Client') as mock_client:
            # Sustituye temporalmente el cliente real de IA por uno simulado
            mock_client.return_value.models.generate_content.return_value = (
                response_mock(json.dumps(mock_suggestion))
            )

            # Comprobamos que el servicio también valida el contenido,
            # no solamente que la respuesta tenga un JSON correcto.
            with pytest.raises(ErrorGenerationAI):
                generate_suggestion_ai(ticket)
