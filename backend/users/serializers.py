from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    """significa "acepto este campo cuando me lo mandan, 
    pero jamás lo incluyo de vuelta en una respuesta". 
    Sin esto, tu API devolvería la contraseña (aunque sea la que el usuario mismo mandó)
    en el JSON de respuesta — un descuido de seguridad sorprendentemente común"""
    
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        """esta es la diferencia que importa: create_user hashea la contraseña automáticamente 
        (usando el mismo mecanismo seguro que ya usa Django internamente);
        create a secas la guardaría en texto plano, y el login nunca funcionaría después."""
        
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )