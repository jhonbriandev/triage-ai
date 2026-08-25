from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, TicketViewSet, CommentaryViewSet

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename = 'categoria')
router.register('tickets', TicketViewSet, basename = 'ticket')
router.register('commentaries', CommentaryViewSet, basename = 'comentario')
 
urlpatterns = router.urls

# GET	/api/tickets/	listar
# POST	/api/tickets/	crear

