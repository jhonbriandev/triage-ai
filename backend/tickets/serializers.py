from rest_framework import serializers
from .models import Category, Ticket, Commentary, SuggestionAi
from django.contrib.auth import get_user_model

# ============================================================
# CATEGORY
# ============================================================

class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category

        # Campos que tendrá la respuesta JSON.
        fields = ['id', 'name']


# ============================================================
# COMMENTARY
# ============================================================

class CommentarySerializer(serializers.ModelSerializer):

    # Campo adicional: no existe directamente en Commentary.
    #
    # author es una relación hacia User, por eso podemos
    # navegar hasta author.username.
    #
    # author       → ID del usuario relacionado
    # author.username → nombre del usuario
    author_username = serializers.CharField(
        source='author.username',
        read_only=True
    )

    class Meta:
        model = Commentary

        fields = [
            'id',
            'ticket',
            'author',
            'author_username',
            'text',
            'created_at'
        ]
        read_only_fields = ['author','created_at']

# ============================================================
# TICKET
# ============================================================

class TicketSerializer(serializers.ModelSerializer):

    # --------------------------------------------------------
    # CAMPOS ADICIONALES
    # --------------------------------------------------------

    # category es una FK.
    # category       → ID de la categoría
    # category.name  → nombre de la categoría
    category_name = serializers.CharField(
        source='category.name',
        read_only=True,
        default=None
    )

    # customer es una FK hacia User.
    # customer          → ID del usuario
    # customer.username → nombre de usuario
    customer_username = serializers.CharField(
        source='customer.username',
        read_only=True
    )

    # assigned_agent es una relación hacia User.
    # username permite mostrar el nombre del agente.
    #
    # default=None evita problemas si no existe un agente asignado.
    assigned_agent_username = serializers.CharField(
        source='assigned_agent.username',
        read_only=True,
        default=None
    )
    suggestion_ai = serializers.SerializerMethodField()
    # --------------------------------------------------------
    # CAMPOS DERIVADOS DE choices
    # --------------------------------------------------------
    #
    # Si el modelo tiene:
    #
    # status = models.CharField(choices=Status.choices)
    #
    # Django crea automáticamente:
    #
    # get_status_display()
    #
    # Ejemplo:
    # status        → 'abierto'
    # status_display → 'Abierto'

    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )

    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )

    #Saber si tiene sugerencia
    has_suggestion_ai = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket

        # Campos originales del modelo + campos adicionales
        # definidos arriba.
        fields = [
            'id',
            'title',
            'description',

            # Estado interno y texto visible.
            'status',
            'status_display',

            # Prioridad interna y texto visible.
            'priority',
            'priority_display',

            # Categoría: ID + nombre.
            'category',
            'category_name',

            # Cliente: ID + username.
            'customer',
            'customer_username',

            # Agente: ID + username.
            'assigned_agent',
            'assigned_agent_username',

            'created_at',
            'has_suggestion_ai',
            
            'suggestion_ai',
            ]

        # Estos campos pueden aparecer en la respuesta,
        # pero el cliente no puede modificarlos mediante
        # POST, PUT o PATCH.
        read_only_fields = [
            'customer',
            'created_at',
            'has_suggestion_ai',
            'customer',
            'assigned_agent',
            'assigned_agent_username',
            
        ]
    def get_has_suggestion_ai(self, obj):
        # suggestion_ai tal como el related name de SuggestionAi
        return hasattr(obj,'suggestion_ai')

    def get_suggestion_ai(self, obj):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            return None
        # Un cliente nunca ve el analisis interno de la IA -- eso es
        # informacion de triage para el equipo de soporte, no para el
        # cliente que reporto el problema.
        if request.user.profile.role not in ('agent', 'admin'):
            return None
        if hasattr(obj, 'suggestion_ai'):
            return SuggestionAiSerializer(obj.suggestion_ai).data
        return None
    

# get_user_model() devuelve el modelo de usuario que Django está usando
# en este proyecto. Se usa esto en vez de "import User directo" porque
# es la forma recomendada por Django: si en el futuro cambias de modelo
# de usuario, este código sigue funcionando sin tocarlo.
User = get_user_model()

# ============================================================
# AGENT (lista simple para el selector de asignación del admin)
# ============================================================

class AgentSerializer(serializers.ModelSerializer):
    """
    El admin solo necesita ver id + username de cada agente para
    poder elegir a quién asignar un ticket. Por eso NO reusamos
    un serializer de User completo (que podría exponer email,
    permisos, etc.) — este es minimalista a propósito.
    """
    class Meta:
        model = User
        fields = ['id', 'username']  # lo mínimo necesario para el <select>
        
        
# ============================================================
# SUGGESTION AI
# ============================================================

class SuggestionAiSerializer(serializers.ModelSerializer):

    class Meta:
        model = SuggestionAi

        fields = [
            'id',
            'ticket',
            'suggestion_category',
            'suggestion_priority',
            'generated_summary',
            'suggestion_answer',
            'generation_date',
            'updated_at',
        ]

        # Aquí:
        #
        # read_only_fields = fields
        #
        # significa que TODOS los campos incluidos en fields
        # serán únicamente de lectura.
        #
        # El serializer puede mostrarlos en la respuesta,
        # pero el cliente no puede modificarlos.

        read_only_fields = fields