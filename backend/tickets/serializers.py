from rest_framework import serializers
from .models import Category, Ticket, Commentary, SuggestionAi


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
        read_only_fields = ['author']

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
        read_only=True
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
            'has_suggestion_ia',
            
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
            
        ]
    def get_has_suggestion_ai(self, obj):
        # suggestion_ai tal como el related name de SuggestionAi
        return hasattr(obj,'suggestion_ai')

    def get_suggestion_ai(self, obj):
        if hasattr(obj, 'suggestion_ai'):
            return SuggestionAiSerializer(obj.suggestion_ai).data
        return None
    
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