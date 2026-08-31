from rest_framework import permissions


class PermissionTicket(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        rol = request.user.profile.rol
        if rol == 'admin':
            return True
        if rol == 'agent':
            return obj.assigned_agent_id == request.user.id
        if rol == 'customer':
            if request.method in permissions.SAFE_METHODS:
                return obj.customer_id == request.user.id
            return False
        return False

class PermissionCommentary(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        rol = request.user.profile.rol
        ticket = obj.ticket
        if rol == 'admin':
            return True
        if rol == 'agent':
            return ticket.assigned_agent_id == request.user.id
        if rol == 'customer':
            return ticket.customer_id == request.user.id
        return False


class PermissionCategory(permissions.BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.profile.rol == 'admin'