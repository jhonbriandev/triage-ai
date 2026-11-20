
import pytest
import json

from unittest.mock import patch, MagicMock

from rest_framework.test import APIClient

from tickets.models import Ticket, SuggestionAi
from tickets.tests.factories import (
    CategoryFactory,
    TicketFactory,
    AgentFactory,
    UserFactory,
    AdminFactory,
)


def response_mock(text):
    # Creamos una respuesta falsa que imita la respuesta de Gemini.
    # Utilizamos el mismo helper que en test_services.py.
    response = MagicMock()
    response.text = text

    return response


@pytest.fixture
def api_client():
    # APIClient permite simular peticiones HTTP a nuestra API.
    return APIClient()


@pytest.mark.django_db
class TestListTickets:

    def test_customer_only_sees_his_tickets(self, api_client):
        customer = UserFactory()
        other_customer = UserFactory()

        # Creamos un ticket propio y otro de un cliente diferente.
        own_ticket = TicketFactory(customer=customer)
        TicketFactory(customer=other_customer)

        api_client.force_authenticate(user=customer)

        response = api_client.get('/api/tickets/')

        assert response.status_code == 200

        # Comprobamos que el cliente solamente vea sus propios tickets.
        ticket_ids = [ticket['id'] for ticket in response.data]

        assert ticket_ids == [own_ticket.id]

    def test_admin_sees_every_ticket(self, api_client):
        admin = AdminFactory()

        # Creamos dos tickets que el administrador debería visualizar.
        TicketFactory()
        TicketFactory()

        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/tickets/')

        assert response.status_code == 200
        assert len(response.data) == 2

    def test_unauthenticated_user_receives_401(self, api_client):
        # Sin autenticación, el endpoint debe rechazar la solicitud.
        response = api_client.get('/api/tickets/')

        assert response.status_code == 401


@pytest.mark.django_db
class TestTicketPermissions:

    def test_customer_cannot_see_stranger_ticket(self, api_client):
        customer = UserFactory()

        # El ticket pertenece a otro usuario.
        stranger_ticket = TicketFactory()

        api_client.force_authenticate(user=customer)

        response = api_client.get(
            f'/api/tickets/{stranger_ticket.id}/'
        )

        # Devolvemos 404 para no revelar que el ticket existe.
        assert response.status_code == 404

    def test_customer_cannot_change_status_of_his_ticket(self, api_client):
        customer = UserFactory()
        ticket = TicketFactory(customer=customer)

        api_client.force_authenticate(user=customer)

        response = api_client.patch(
            f'/api/tickets/{ticket.id}/',
            {'status': 'cerrado'},
            format='json',
        )

        # El cliente puede consultar su ticket, pero no cambiar su estado.
        assert response.status_code == 403

    def test_assigned_agent_can_change_ticket_status(self, api_client):
        agent = AgentFactory()
        ticket = TicketFactory(assigned_agent=agent)

        api_client.force_authenticate(user=agent)

        response = api_client.patch(
            f'/api/tickets/{ticket.id}/',
            {'status': 'en_progreso'},
            format='json',
        )

        # El agente asignado tiene autorización para cambiar el estado.
        assert response.status_code == 200
        assert response.data['status'] == 'en_progreso'


@pytest.mark.django_db
class TestCommentaries:

    def test_customer_cannot_comment_on_stranger_ticket(self, api_client):
        customer = UserFactory()
        stranger_ticket = TicketFactory()

        api_client.force_authenticate(user=customer)

        response = api_client.post(
            '/api/commentaries/',
            {
                'ticket': stranger_ticket.id,
                'text': 'Intento colarme',
            },
            format='json',
        )

        # Un cliente no puede comentar en un ticket ajeno.
        assert response.status_code == 403


@pytest.mark.django_db
class TestCreateTicket:

    def test_ticket_is_created_without_suggestion_if_ai_fails(self, api_client):
        customer = UserFactory()
        category = CategoryFactory()

        api_client.force_authenticate(user=customer)

        with patch('tickets.services.genai.Client') as mock_client:

            # Simulamos que Gemini no responde por un error de conexión.
            mock_client.return_value.models.generate_content.side_effect = (
                Exception('Network error')
            )

            response = api_client.post(
                '/api/tickets/',
                {
                    'title': 'Prueba',
                    'description': 'x',
                    'category': category.id,
                },
                format='json',
            )

        # Aunque la IA falle, el ticket debe crearse correctamente.
        assert response.status_code == 201
        assert response.data['has_suggestion_ai'] is False

        ticket = Ticket.objects.get(customer=customer)

        assert ticket.title == 'Prueba'
        
        assert Ticket.objects.count() == 1
        assert SuggestionAi.objects.count() == 0
        
        # No debe existir una sugerencia asociada al ticket.
        assert not SuggestionAi.objects.filter(ticket=ticket).exists()

    def test_ticket_is_created_with_suggestion_if_ai_responds(self, api_client):
        customer = UserFactory()
        category = CategoryFactory()

        api_client.force_authenticate(user=customer)

        # Utilizamos exactamente la misma estructura JSON del Service Test.
        mock_suggestion = {
            "suggestion_category": "Bug",
            "suggestion_priority": "alta",
            "generated_summary": "Resumen del problema",
            "suggestion_answer": "Revisar la conexión del servicio."
        }

        with patch('tickets.services.genai.Client') as mock_client:

            # Simulamos una respuesta válida de Gemini.
            mock_client.return_value.models.generate_content.return_value = (
                response_mock(json.dumps(mock_suggestion))
            )

            response = api_client.post(
                '/api/tickets/',
                {
                    'title': 'Prueba',
                    'description': 'x',
                    'category': category.id,
                },
                format='json',
            )

        # Comprobamos que la API creó el ticket y generó la sugerencia.
        assert response.status_code == 201
        assert response.data['has_suggestion_ai'] is True

        ticket = Ticket.objects.get(customer=customer)

        assert ticket.title == 'Prueba'

        # Comprobamos que solo exista 1 sugerencia de IA
        assert SuggestionAi.objects.count() == 1
        
        # Comprobamos que existe una sugerencia asociada al ticket.
        suggestion = SuggestionAi.objects.get(ticket=ticket)

        # Comprobamos que los cuatro campos coinciden con la respuesta de IA.
        assert suggestion.suggestion_category == mock_suggestion['suggestion_category']
        assert suggestion.suggestion_priority == mock_suggestion['suggestion_priority']
        assert suggestion.generated_summary == mock_suggestion['generated_summary']
        assert suggestion.suggestion_answer == mock_suggestion['suggestion_answer']

    def test_ticket_is_created_without_suggestion_if_ai_returns_invalid_output(self, api_client):
        customer = UserFactory()
        category = CategoryFactory()

        api_client.force_authenticate(user=customer)

        with patch('tickets.services.genai.Client') as mock_client:

            # Simulamos que Gemini responde, pero no devuelve un JSON válido.
            mock_client.return_value.models.generate_content.return_value = (
                response_mock('This is not valid JSON')
            )

            response = api_client.post(
                '/api/tickets/',
                {
                    'title': 'Prueba',
                    'description': 'x',
                    'category': category.id,
                },
                format='json',
            )

        # El error de IA no debe impedir la creación del ticket.
        assert response.status_code == 201
        
        # # Ademas tampoco debe responder error del servidor
        # assert response.status_code != 500
        
        assert response.data['has_suggestion_ai'] is False

        ticket = Ticket.objects.get(customer=customer)

        assert ticket.title == 'Prueba'

        # Una respuesta inválida no debe generar registros de sugerencias.
        assert not SuggestionAi.objects.filter(ticket=ticket).exists()

    def test_critical_ticket_is_created_with_urgent_priority(self,api_client):
        customer = UserFactory()
        category = CategoryFactory()
    
        api_client.force_authenticate(user=customer)
    
        with patch('tickets.services.genai.Client') as mock_client:
    
            # Simulamos que Gemini no responde por un error de conexión.
            mock_client.return_value.models.generate_content.side_effect = (
                Exception('Network error')
            )
            response = api_client.post(
                '/api/tickets/',
                {
                    'title': 'Caida total del sistema',
                    'description': 'No funciona nada',
                    'category': category.id,
                },
                format='json',
            )
    
        # Aunque la IA falle, el ticket debe crearse correctamente.
        assert response.status_code == 201
        assert response.data['priority'] == 'urgente'

    def test_normal_ticket_keeps_default_priority(self,api_client):
        customer = UserFactory()
        category = CategoryFactory()
    
        api_client.force_authenticate(user=customer)
    
        with patch('tickets.services.genai.Client') as mock_client:
    
            # Simulamos que Gemini no responde por un error de conexión.
            mock_client.return_value.models.generate_content.side_effect = (
                Exception('Network error')
            )
            response = api_client.post(
                '/api/tickets/',
                {
                    'title': 'Duda sobre mi factura',
                    'description': 'Quiero saber la fecha de corte',
                    'category': category.id,
                },
                format='json',
            )
    
        # Aunque la IA falle, el ticket debe crearse correctamente.
        assert response.status_code == 201
        assert response.data['priority'] == 'media'
        
    # USANDO XFAIL, CORREGIDO PORQUE SE IMPLEMENTO QUE LA VIEW MANDE    
    # @pytest.mark.parametrize(
    # "text",
    # [
    #     pytest.param(
    #         "urgente",
    #         marks=pytest.mark.xfail(
    #             reason="El cliente puede establecer la prioridad mediante JSON"
    #         )
    #     ),pytest.param(
    #                 "cerrado",
    #                 marks=pytest.mark.xfail(
    #                     reason="El cliente puede establecer el estado mediante JSON"
    #                 )
    #             )
    # ]
    # )
    # def test_customer_cannot_set_priority_or_status_when_creating_ticket(
    #     self, api_client, text
    # ):
    #     customer = UserFactory()
    #     category = CategoryFactory()

    #     api_client.force_authenticate(user=customer)

    #     with patch('tickets.services.genai.Client') as mock_client:

    #         # Simulamos que Gemini no responde por un error de conexión.
    #         mock_client.return_value.models.generate_content.side_effect = (
    #             Exception('Network error')
    #         )

    #         response = api_client.post(
    #             '/api/tickets/',
    #             {
    #             'title': 'Duda sobre mi factura',
    #             'description': 'Quiero saber la fecha de corte',
    #             'category': category.id,
    #             'priority': 'urgente',
    #             'status': 'cerrado'
    #             },
    #             format='json',
    #         )

    #     # Aunque la IA falle, el ticket debe crearse correctamente.
    #     assert response.status_code == 201
    #     assert response.data['priority'] == 'media'
    #     assert response.data['status'] == 'cerrado'
    
    def test_customer_cannot_set_priority_or_status_when_creating_ticket(
        self, api_client
    ):
        customer = UserFactory()
        category = CategoryFactory()

        api_client.force_authenticate(user=customer)

        with patch('tickets.services.genai.Client') as mock_client:

            # Simulamos que Gemini no responde por un error de conexión.
            mock_client.return_value.models.generate_content.side_effect = (
                Exception('Network error')
            )

            response = api_client.post(
                '/api/tickets/',
                {
                'title': 'Duda sobre mi factura',
                'description': 'Quiero saber la fecha de corte',
                'category': category.id,
                'priority': 'urgente',
                'status': 'cerrado'
                },
                format='json',
            )

        # Aunque la IA falle, el ticket debe crearse correctamente.
        assert response.status_code == 201

        # El servidor determina la prioridad y el estado.
        assert response.data['priority'] == 'media'
        assert response.data['status'] == 'abierto'

