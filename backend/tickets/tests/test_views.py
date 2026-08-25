import pytest
from rest_framework.test import APIClient

from tickets.tests.factories import (
    CategoryFactory,
    TicketFactory,
    CommentaryFactory,
    AgentFactory,
    UserFactory,
    AdminFactory,
)


@pytest.fixture
def api_client():
    # APIClient simula peticiones HTTP a nuestra API sin levantar un servidor.
    return APIClient()


@pytest.mark.django_db
class TestListTickets:

    def test_customer_only_see_his_tickets(self, api_client):
        customer1 = UserFactory()
        customer2 = UserFactory()

        # Creamos un ticket propio y otro perteneciente a otro cliente.
        own_ticket = TicketFactory(customer=customer1)
        TicketFactory(customer=customer2)

        # Simulamos que customer1 está autenticado.
        api_client.force_authenticate(user=customer1)

        response = api_client.get('/api/tickets/')

        assert response.status_code == 200

        # La API debe devolver únicamente los tickets del cliente autenticado.
        ids = [t['id'] for t in response.data]
        assert ids == [own_ticket.id]

    def test_admin_see_every_ticket(self, api_client):
        admin = AdminFactory()

        # Creamos dos tickets que el administrador debería poder ver.
        TicketFactory()
        TicketFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/tickets/')

        assert response.status_code == 200
        assert len(response.data) == 2

    def test_without_authenticate_return_401(self, api_client):
        # Sin autenticación, el acceso al endpoint debe ser rechazado.
        response = api_client.get('/api/tickets/')

        assert response.status_code == 401


@pytest.mark.django_db
class TestPermissionInTicket:

    def test_customer_cannot_see_stranger_ticket(self, api_client):
        customer = UserFactory()

        # El ticket pertenece a otro usuario.
        stranger_ticket = TicketFactory()

        api_client.force_authenticate(user=customer)

        response = api_client.get(
            f'/api/tickets/{stranger_ticket.id}/'
        )

        # Se devuelve 404 para no revelar que el ticket existe.
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

        # El cliente puede ver su ticket, pero no modificar su estado.
        assert response.status_code == 403

    def test_assigned_agent_can_change_status_his_ticket(self, api_client):
        agent = AgentFactory()
        ticket = TicketFactory(assigned_agent=agent)

        api_client.force_authenticate(user=agent)

        response = api_client.patch(
            f'/api/tickets/{ticket.id}/',
            {'status': 'en_progreso'},
            format='json',
        )

        # El agente asignado sí tiene permiso para cambiar el estado.
        assert response.status_code == 200
        assert response.data['status'] == 'en_progreso'


@pytest.mark.django_db
class TestCommentaries:

    def test_customer_cannot_comment_in_stranger_ticket(self, api_client):
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

        # Un cliente no puede comentar en un ticket que no le pertenece.
        assert response.status_code == 403