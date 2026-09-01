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
    permission_classes = [PermissionCategory]

class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [PermissionTicket]
    
    def get_queryset(self):
        user = self.request.user
        role = user.profile.role
        if role == 'admin':
            return Ticket.objects.all()
        if role == 'agent':
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
        role = user.profile.role
        base = Commentary.objects.select_related('ticket', 'author')
        if role == 'admin':
            queryset = base
        elif role == 'agent':
            queryset = base.filter(ticket__assigned_agent=user)
        else :
            queryset = base.filter(ticket__customer=user)
            
        ticked_id = self.request.query_params.get('ticket')
        if ticked_id:
            queryset = queryset.filter(ticket_id=ticked_id)
        return queryset
    
    def perform_create(self,serializer):
        ticket = serializer.validated_data['ticket']
        user = self.request.user
        role = user.profile.role
        can_comment= (
            role == 'admin' or (role == 'agent' and ticket.assigned_agent_id ==  user.id)
                            or (role == 'customer' and ticket.customer_id == user.id))
        if not can_comment:
            raise PermissionDenied('No puedes comentar en un ticket que no es tuyo.')
        serializer.save(author = user)