import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient
from tickets.services import generate_suggestion_ia, ErrorGenerationIA
from tickets.tests.factories import UserFactory, CategoryFactory, TicketFactory


def response_mock(texto):
    # Crea una respuesta falsa que imita la respuesta de la API de IA.
    r = MagicMock()
    r.text = texto
    return r


@pytest.mark.django_db
class TestGenerateSuggestionIA:

    def test_camino_feliz_devuelve_las_4_claves(self):
        ticket = TicketFactory()

        json_valido = (
            '{"suggestion_category": "Bug", "suggestion_priority": "alta", '
            '"generated_summary": "resumen", "suggestion_answer": "respuesta"}'
        )

        # Sustituimos temporalmente el cliente real de GenAI por un Mock.
        # Así el test no hace ninguna llamada real a la API.
        with patch('tickets.services.genai.Client') as MockClient:

            # Configuramos qué debe devolver la API falsa.
            MockClient.return_value.models.generate_content.return_value = (
                response_mock(json_valido)
            )

            results = generate_suggestion_ia(ticket)

        assert results['suggestion_priority'] == 'alta'

    def test_error_api_launch_error_generation_ai(self):
        ticket = TicketFactory()

        # Simulamos que la API de IA falla al generar la respuesta.
        with patch('tickets.services.genai.Client') as MockClient:
            MockClient.return_value.models.generate_content.side_effect = (
                Exception('fallo de red')
            )

            with pytest.raises(ErrorGenerationIA):
                generate_suggestion_ia(ticket)

    def test_invalid_priority_launch_error_generation_ai(self):
        ticket = TicketFactory()

        bad_priority = (
            '{"suggestion_category": "Bug", "suggestion_priority": "SUPER URGENTE", '
            '"generated_summary": "x", "suggestion_answer": "y"}'
        )

        # La API no falla, pero devuelve información inválida.
        with patch('tickets.services.genai.Client') as MockClient:
            MockClient.return_value.models.generate_content.return_value = (
                response_mock(bad_priority)
            )

            with pytest.raises(ErrorGenerationIA):
                generate_suggestion_ia(ticket)


@pytest.mark.django_db
class TestCreationTicketWithIA:

    def test_ticket_is_created_without_suggestion_if_ai_fails(self):
        # Factory: necesitamos datos reales para probar la creación del ticket.
        customer = UserFactory()
        category = CategoryFactory()

        client = APIClient()
        client.force_authenticate(user=customer)

        # Mock: simulamos que la IA no responde.
        # No queremos depender de una API externa durante el test.
        with patch('tickets.services.genai.Client') as MockClient:
            MockClient.return_value.models.generate_content.side_effect = (
                Exception('la IA no responde')
            )

            response = client.post(
                '/api/tickets/',
                {
                    'title': 'Prueba',
                    'description': 'x',
                    'category': category.id,
                },
                format='json'
            )

        assert response.status_code == 201
        assert response.data['has_suggestion_ia'] is False