from rest_framework import permissions


class PermissionTicket(permissions.BasePermission):
    """
    Controla quién puede VER o MODIFICAR un ticket puntual.

    - Admin: acceso total.
    - Agente: solo a los tickets que tiene asignados (ver y modificar).
    - Cliente: solo a los tickets que él creó, y únicamente para LEER
      (métodos seguros: GET/HEAD/OPTIONS) — nunca para modificar.
    """

    def has_permission(self, request, view):
        # Este método es el primer filtro: se ejecuta ANTES de saber
        # de qué objeto (ticket) se trata. Aquí solo comprobamos algo
        # muy básico: "¿hay alguien identificado haciendo esta
        # petición?". Es como el guardia en la puerta que solo pide
        # tu credencial, sin mirar a qué piso vas.
        
        if not (request.user and request.user.is_authenticated):
            return False

        # Un agente no puede CREAR tickets (POST), pero sí puede seguir
        # usando el resto de acciones (listar, ver detalle, actualizar) —
        # esas se filtran aparte en has_object_permission / get_queryset.
        if request.method == 'POST' and request.user.profile.role == 'agent':
            return False

        return True

    def has_object_permission(self, request, view, obj):
        # Este segundo método SÍ conoce el objeto concreto (obj = el
        # ticket puntual que se está pidiendo/editando). Aquí es
        # donde decidimos el acceso "fino", según el rol del usuario.
        role = request.user.profile.role

        if role == 'admin':
            # El admin puede todo
            return True

        if role == 'agent':
            # obj.assigned_agent_id -> el ID del agente asignado al ticket
            # request.user.id        -> el ID del usuario que hace la petición
            #
            # Si son el mismo número, es SU ticket y puede acceder.
            return obj.assigned_agent_id == request.user.id

        if role == 'customer':
            # SAFE_METHODS son los métodos "de solo lectura":
            # ('GET', 'HEAD', 'OPTIONS'). Es decir, el cliente puede
            # mirar su ticket, pero nunca editarlo ni borrarlo.
            if request.method in permissions.SAFE_METHODS:
                return obj.customer_id == request.user.id
            return False

        return False


class PermissionCommentary(permissions.BasePermission):
    """
    Un comentario hereda la visibilidad de su ticket:
    - Admin: puede comentar en cualquier ticket.
    - Agente: puede comentar en los tickets que tiene asignados.
    - Cliente: puede comentar en los tickets que él creó.
    """

    def has_permission(self, request, view):
        # Igual que antes: primer filtro básico, solo pide estar
        # autenticado.
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        role = request.user.profile.role

        # obj es un Commentary, no un Ticket. Pero un comentario
        # SIEMPRE pertenece a un ticket, así que primero navegamos
        # hasta ese ticket para poder aplicar las mismas reglas.
        ticket = obj.ticket

        if role == 'admin':
            return True
        if role == 'agent':
            return ticket.assigned_agent_id == request.user.id
        if role == 'customer':
            return ticket.customer_id == request.user.id
        return False


class PermissionCategory(permissions.BasePermission):
    """
    Cualquier usuario autenticado puede LEER las categorías (las necesita
    para crear un ticket). Solo el admin puede crear, editar o borrarlas.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        if request.method in permissions.SAFE_METHODS:
            # Cualquiera autenticado puede leer categorías (GET/HEAD/OPTIONS).
            return True

        # Cualquier otro método (POST, PUT, PATCH, DELETE) solo lo puede
        # hacer el admin.
        return request.user.profile.role == 'admin'


# ============================================================
# 🧠 GUÍA RÁPIDA DE CONCEPTOS USADOS EN ESTE ARCHIVO
# ============================================================
#
# request
# -------
# Es el objeto que representa la petición HTTP que llegó (quién la
# hizo, con qué método, qué datos trae, etc.). Piénsalo como el
# "sobre" que llega a la oficina: tiene remitente (request.user) y
# tipo de trámite (request.method).
#
# request.user
# ------------
# El usuario autenticado que está haciendo la petición.
# Ej: request.user.id, request.user.profile.rol
#
# request.method
# ---------------
# El verbo HTTP usado: 'GET', 'POST', 'PUT', 'PATCH', 'DELETE'.
#
# permissions.SAFE_METHODS
# -------------------------
# Una tupla fija que trae DRF: ('GET', 'HEAD', 'OPTIONS').
# Son los métodos que NO modifican nada, solo leen datos.
# if request.method in permissions.SAFE_METHODS:
#     # equivalente conceptual a:
#     # if request.method in ('GET', 'HEAD', 'OPTIONS'):
#
# has_permission vs has_object_permission
# ----------------------------------------
# has_permission()        -> filtro GENERAL, antes de saber el objeto.
# has_object_permission() -> filtro ESPECÍFICO, ya con el objeto en mano.
# DRF llama primero a has_permission(); si pasa, y la vista trabaja
# sobre un objeto puntual, llama también a has_object_permission().
#
# El sufijo _id (ej: assigned_agent_id, customer_id)
# ----------------------------------------------------
# NO lo escribiste tú en el modelo. Es una convención automática de
# Django: cuando declaras un ForeignKey, por ejemplo:
#
#     assigned_agent = models.ForeignKey(User, ...)
#
# Django crea internamente una columna en la base de datos llamada
# assigned_agent_id, que guarda solo el número de ID del usuario
# relacionado.
#
# Por eso tienes DOS formas de acceder al mismo dato:
#
#     ticket.assigned_agent      -> objeto User completo (<User: pedro>)
#     ticket.assigned_agent_id   -> solo su ID (ej: 7)
#
# Comparar por _id (ej: obj.assigned_agent_id == request.user.id) es
# más simple y directo que comparar objetos completos
# (obj.assigned_agent == request.user); ambas formas dan el mismo
# resultado, pero con _id sabes que solo estás comparando dos números.
#
# ============================================================
# 🧠 MAPA MENTAL GENERAL
# ============================================================
#
#                     PETICIÓN
#                        │
#                        ▼
#                  request.user
#                        │
#                        ▼
#                      Profile
#                        │
#                        ▼
#                       rol
#                        │
#           ┌────────────┼────────────┐
#           ▼            ▼            ▼
#         admin        agent       customer
#           │            │            │
#           ▼            ▼            ▼
#         TODO       ticket         ticket
#                    asignado       propio
#                                   │
#                               solo lectura