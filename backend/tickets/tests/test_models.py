import pytest
from django.db.models import ProtectedError
from tickets.models import Commentary
from tickets.tests.factories import (
    CategoryFactory,
    TicketFactory,
    CommentaryFactory,
    AgentFactory,
)


@pytest.mark.django_db
class TestCategory:

    def test_str_return_name(self):
        # Factory: crea una categoría real en la BD de testing.
        category = CategoryFactory(name='Bugs')

        # Comprueba que __str__() devuelve el nombre de la categoría.
        assert str(category) == 'Bugs'

    def test_cannot_delete_category_with_tickets(self):
        category = CategoryFactory()

        # Creamos un ticket relacionado con la categoría.
        TicketFactory(category=category)

        # La relación PROTECT debe impedir eliminar la categoría
        # mientras tenga tickets relacionados.
        with pytest.raises(ProtectedError):
            category.delete()


@pytest.mark.django_db
class TestTicket:

    def test_str_include_id_and_title(self):
        # Creamos un ticket con un título conocido.
        ticket = TicketFactory(title='Mi problema')

        # Comprueba que __str__() incluye el ID y el título.
        assert str(ticket) == f'#{ticket.pk} - Mi problema'

    def test_status_for_default_is_open(self):
        # La factory crea el ticket usando el estado por defecto del modelo.
        ticket = TicketFactory()

        # Comprueba que el estado inicial sea "abierto".
        assert ticket.status == 'abierto'

    def test_if_assigned_agent_delete_ticket_no_delete(self):
        # Creamos un agente y un ticket asignado a ese agente.
        agent = AgentFactory()
        ticket = TicketFactory(assigned_agent=agent)

        # Eliminamos el agente. El ticket debe seguir existiendo.
        agent.delete()

        # Recargamos el ticket desde la BD para obtener su estado actualizado.
        ticket.refresh_from_db()

        # La relación debe quedar en None en lugar de eliminar el ticket.
        assert ticket.assigned_agent is None


@pytest.mark.django_db
class TestCommentary:

    def test_delete_ticket_too_delete_commentaries(self):
        ticket = TicketFactory()

        # Creamos un comentario relacionado con el ticket.
        CommentaryFactory(ticket=ticket)

        # Guardamos el ID antes de eliminar el ticket.
        ticket_id = ticket.id

        # CASCADE debe eliminar automáticamente sus comentarios.
        ticket.delete()

        # Comprobamos que ya no existe ningún comentario asociado al ticket.
        assert Commentary.objects.filter(ticket_id=ticket_id).count() == 0