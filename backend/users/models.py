from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):

    # Roles disponibles para los usuarios.
    # Estructura: NOMBRE = 'valor_en_BD', 'texto_visible'
    class Role(models.TextChoices):
        CUSTOMER = 'customer', 'Customer'
        AGENT = 'agent', 'Agent'
        ADMINISTRATOR = 'admin', 'Administrator'

    # Relación 1 a 1 con el usuario de Django.
    # user.profile permite acceder al perfil desde el usuario.
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )

    # Rol del usuario. Por defecto será CUSTOMER.
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER
    )

    # Representación del perfil: username + rol visible.
    def __str__(self):
        return f'{self.user.username} ({self.get_role_display()})'