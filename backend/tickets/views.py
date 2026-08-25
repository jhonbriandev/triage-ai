import logging
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from .models import Category, Ticket, Commentary, SuggestionAi
from .serializers import CategorySerializer, TicketSerializer, CommentarySerializer
from .permissions import PermissionCategory, PermissionTicket, PermissionCommentary
from .services import generate_suggestion_ia, ErrorGenerationIA

logger = logging.getLogger(__name__)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_class = [PermissionCategory]

class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [PermissionTicket]
    
    def get_queryset(self):
        user = self.request.user
        rol = user.profile.rol
        if rol == 'admin':
            return Ticket.objects.all()
        if rol == 'agent':
            return Ticket.objects.filter(assigned_agent = user)
        return Ticket.objects.filter(customer = user)
    
    def perform_create(self, serializer):
        ticket = serializer.save(customer=self.request.user)
        try:
            datos_ia = generate_suggestion_ia(ticket)
            SuggestionAi.objects.create(ticket=ticket, **datos_ia)
        except ErrorGenerationIA as exc:
            logger.error('Ticket #%s creado SIN sugerencia de IA: %s', ticket.pk, exc)
        
class CommentaryViewSet(viewsets.ModelViewSet):
    serializer_class = CommentarySerializer
    permission_classes = [PermissionCommentary] 
    
    def get_queryset(self):
        user = self.request.user
        rol = user.profile.rol
        if rol == 'admin':
            return Commentary.objects.all()
        if rol == 'agent':
            return Commentary.objects.filter(ticket__assigned_agent = user)
        return Commentary.objects.filter(ticket__customer = user)
    
    def perform_create(self,serializer):
        ticket = serializer.validated_data['ticket']
        user = self.request.user
        rol = user.profile.rol
        can_comment= (
            rol == 'admin' or (rol == 'agent' and ticket.assigned_agent_id ==  user.id)
                            or (rol == 'customer' and ticket.customer_id == user.id))
        if not can_comment:
            raise PermissionDenied('No puedes comentar en un ticket que no es tuyo.')
        serializer.save(author = user)