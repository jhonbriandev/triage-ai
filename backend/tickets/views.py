import logging
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from .models import Category, Ticket, Commentary, SuggestionAi
from .serializers import CategorySerializer, TicketSerializer, CommentarySerializer, AgentSerializer
from .permissions import PermissionCategory, PermissionTicket, PermissionCommentary, PermissionAssignTicket
from .services import generate_suggestion_ai, ErrorGenerationAI
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

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

        # --------------------------------------------------------
        # BLOQUE 1: filtro base según el rol del usuario
        # --------------------------------------------------------
        # Cada rol ve un subconjunto distinto de tickets:
        # - admin: todos los tickets del sistema
        # - agent: solo los tickets que tiene asignados
        # - customer: solo los tickets que él mismo creó
        # Nota: ya NO usamos "return" aquí dentro. Antes cada rama
        # entregaba el resultado de inmediato y cortaba la función;
        # ahora solo lo guardamos en "queryset" para poder seguir
        # afinándolo en el Bloque 2 antes de entregarlo.
        if role == 'admin':
            queryset = Ticket.objects.all()
        elif role == 'agent':
            queryset = Ticket.objects.filter(assigned_agent=user)
        else:
            queryset = Ticket.objects.filter(customer=user)

        # --------------------------------------------------------
        # BLOQUE 2: filtro opcional por estado (?status=abierto)
        # --------------------------------------------------------
        # query_params.get('status') lee el parámetro que llega en la
        # URL de la petición (ej. /tickets/?status=abierto). Si no viene
        # ese parámetro, devuelve None y el "if" no se ejecuta, dejando
        # el queryset intacto (mismo comportamiento que antes).
        # Si SÍ viene, filtramos el queryset ya calculado en el Bloque 1,
        # así el filtro por estado se aplica sin importar el rol.
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # --------------------------------------------------------
        # BLOQUE 3: entrega final
        # --------------------------------------------------------
        # Un solo punto de salida, ya con ambos filtros aplicados
        # (rol + estado, si corresponde).
        return queryset
    
    def perform_create(self, serializer):
        ticket = serializer.save(customer=self.request.user)
        try:
            datos_ia = generate_suggestion_ai(ticket)
            SuggestionAi.objects.create(ticket=ticket, **datos_ia)
        except ErrorGenerationAI as exc:
            logger.error('Ticket #%s creado SIN sugerencia de IA: %s', ticket.pk, exc)
        
    @action(detail=False, methods=['get'])
    def stats(self, request):
        queryset = self.get_queryset()
        counts = queryset.values('status').annotate(total=Count('id'))

        result = {value: 0 for value, _ in Ticket.Status.choices}
        for row in counts:
            result[row['status']] = row['total']

        return Response(result)
    
    @action(detail=False, methods=['get'], permission_classes=[PermissionAssignTicket])
    def agents(self, request):
        # detail=False -> no necesita un ID de ticket en la URL.
        # Esto crea automáticamente la ruta GET /tickets/agents/
        # (mismo patrón que ya usas en tu action "stats").
        #
        # Solo el admin puede llamar esto: reutilizamos
        # PermissionAssignTicket porque si solo el admin puede
        # ASIGNAR, tiene sentido que solo el admin pueda VER
        # esta lista (un agente no necesita saber quiénes son
        # sus compañeros).
        agents = User.objects.filter(profile__role='agent')
        return Response(AgentSerializer(agents, many=True).data)

    @action(detail=True, methods=['patch'], permission_classes=[PermissionAssignTicket])

    def assign(self, request, pk=None):
        ticket = self.get_object()
        agent_id = request.data.get('assigned_agent')
        
        # Antes: cualquier valor vacío caía directo al User.objects.get()
        # y fallaba. Ahora lo manejamos como un caso válido aparte:
        # "sin agente" es una asignación legítima, no un error.
        if agent_id in (None, "", "null"):
            ticket.assigned_agent = None
            ticket.save()
            return Response(TicketSerializer(ticket).data)
        
        try:
            # Validamos que el ID recibido sea realmente un agente,
            # no cualquier usuario (ej. un cliente por error).
            # profile__role='agent' -> filtra dentro de la tabla
            # Profile relacionada, no en User directamente.
            agent = User.objects.get(id=agent_id, profile__role='agent')
        except User.DoesNotExist:
            return Response(
                {"error": "El usuario indicado no existe o no es un agente."},
                status=400
            )

        ticket.assigned_agent = agent
        ticket.save()
        return Response(TicketSerializer(ticket).data)
    
    
    
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