from django.urls import path
from .views import RegisterView

urlpatterns = [
    # Para acceder a este endpoint usar http://127.0.0.1:8000/api/users/register/
    path('register/', RegisterView.as_view(), name='register'),
]