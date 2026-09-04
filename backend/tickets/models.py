from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Ticket(models.Model):
    class Status(models.TextChoices):
        ABIERTO = 'abierto', 'Abierto'
        EN_PROGRESO = 'en_progreso', 'En progreso'
        RESUELTO = 'resuelto', 'Resuelto'
        CERRADO = 'cerrado', 'Cerrado'

    class Priority(models.TextChoices):
        BAJA = 'baja', 'Baja'
        MEDIA = 'media', 'Media'
        ALTA = 'alta', 'Alta'
        URGENTE = 'urgente', 'Urgente'

    customer = models.ForeignKey(User,on_delete=models.PROTECT, related_name='created_tickets')
    # No es protect, por lo cual si se borra un agente asignado el ticket no se borrara
    assigned_agent = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    category = models.ForeignKey(Category,on_delete=models.PROTECT, null=True, blank=True, related_name='tickets')
    title = models.CharField(max_length= 200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices= Status.choices, default=Status.ABIERTO)
    priority = models.CharField(max_length=20, choices=Priority.choices, default= Priority.MEDIA)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'#{self.pk} - {self.title}'

class Commentary(models.Model):

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='commentaries')
    author = models.ForeignKey(User,on_delete= models.PROTECT, related_name='commentaries')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Comentario de {self.author} en Ticket de {self.ticket_id}'


class SuggestionAi(models.Model):

    ticket = models.OneToOneField(Ticket, on_delete=models.CASCADE, related_name='suggestion_ai')
    suggestion_category = models.CharField(max_length=100)
    suggestion_priority = models.CharField(max_length=20)
    generated_summary = models.TextField()
    suggestion_answer = models.TextField()
    generation_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Sugerencia IA - Ticket {self.ticket_id}'
