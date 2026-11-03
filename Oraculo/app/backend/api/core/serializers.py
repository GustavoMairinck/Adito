from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Removemos o campo username e adicionamos o email
        self.fields.pop('username', None)
        self.fields['email'] = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        # Tenta autenticar usando o email como username
        # (Se o seu Django estiver configurado para ter o email único)
        user = authenticate(username=email, password=password)
        
        if not user:
            # Caso o username no banco não seja o email, tentamos buscar pelo campo email
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if user:
            if not user.is_active:
                raise serializers.ValidationError('Usuário inativo.')
            
            refresh = self.get_token(user)
            data = {}
            data['refresh'] = str(refresh)
            data['access'] = str(refresh.access_token)
            data['token'] = data['access']  # Para compatibilidade com o Front
            
            # Adicionamos informações extras úteis para o front
            data['user'] = {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'role': 'admin' if user.is_staff else 'user',
                'avatar': '',
                'tenant': user.tenant.name if user.tenant else None
            }
            
            return data
        
        raise serializers.ValidationError('Credenciais inválidas.')
