import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User
from users.models import Profile
from tickets.models import Category, Ticket, Commentary


class UserFactory(DjangoModelFactory):
    """Crea un usuario customer (el rol por defecto de Perfil)."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f'usuario{n}')
    email = factory.Faker('email', locale='es_ES')
    password = factory.PostGenerationMethodCall('set_password', 'clave12345')

    @factory.post_generation
    def save_password(self, create, extracted, **kwargs):
        if create:
            self.save()


class AgentFactory(UserFactory):
    """Igual que UserFactory, pero sube el rol a 'agente' después de crearse."""

    @factory.post_generation
    def be_agent(self, create, extracted, **kwargs):
        if create:
            self.profile.role = Profile.Role.AGENT
            self.profile.save()


class AdminFactory(UserFactory):
    """Igual que UserFactory, pero sube el role a 'admin' después de crearse."""

    @factory.post_generation
    def be_admin(self, create, extracted, **kwargs):
        if create:
            self.profile.role = Profile.Role.ADMINISTRATOR
            self.profile.save()


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category
        django_get_or_create = ('name',)

    name = factory.Faker('word', locale='es_ES')


class TicketFactory(DjangoModelFactory):
    class Meta:
        model = Ticket

    title = factory.Faker('sentence', nb_words=6, locale='es_ES')
    description = factory.Faker('paragraph', locale='es_ES')
    category = factory.SubFactory(CategoryFactory)
    customer = factory.SubFactory(UserFactory)


class CommentaryFactory(DjangoModelFactory):
    class Meta:
        model = Commentary

    ticket = factory.SubFactory(TicketFactory)
    author = factory.SubFactory(UserFactory)
    text = factory.Faker('paragraph', locale='es_ES')