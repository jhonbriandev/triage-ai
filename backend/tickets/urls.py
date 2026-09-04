from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, TicketViewSet, CommentaryViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename = 'categoria')
router.register('tickets', TicketViewSet, basename = 'ticket')
router.register('commentaries', CommentaryViewSet, basename = 'comentario')
 
urlpatterns = router.urls

# basename sirve para que el router nombre las rutas de tu ViewSet 
# (comentarios-list, comentarios-detail), especialmente cuando no hay queryset.
# Es equivalente a "comentario-detail" → "/comentarios/<pk>/"
# Esos nombres se usan para resolver/referenciar URLs (por ejemplo con reverse() o serializers),
# aunque normalmente DRF lo hace automáticamente.

