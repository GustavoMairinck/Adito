import os
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

_IS_DEV = os.environ.get('DJANGO_DEBUG', 'false').lower() == 'true'

# Tempo de vida dos cookies em segundos (deve coincidir com as configurações JWT)
ACCESS_MAX_AGE = 60 * 60 * 24       # 1 dia
REFRESH_MAX_AGE = 60 * 60 * 24 * 7  # 7 dias


def _cookie_kwargs(max_age: int) -> dict:
    """Retorna kwargs comuns para setar cookies de autenticação."""
    return {
        'httponly': True,
        'samesite': 'Lax',
        # Em produção secure=True; em dev pode ser False (HTTP)
        'secure': not _IS_DEV,
        'max_age': max_age,
        'path': '/',
    }


def _delete_auth_cookies(response):
    response.set_cookie('access_token', '', max_age=0, path='/', secure=not _IS_DEV, httponly=True, samesite='Lax')
    response.set_cookie('refresh_token', '', max_age=0, path='/', secure=not _IS_DEV, httponly=True, samesite='Lax')


@csrf_exempt
@require_POST
def cookie_login(request):
    """Login via email/senha → seta access e refresh tokens como HttpOnly Cookies.

    Retorna apenas os dados não-sensíveis do usuário no body JSON.
    O token em si nunca é enviado ao JavaScript — apenas seta cookies HttpOnly.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'message': 'Requisição inválida.'}, status=400)

    email = body.get('email', '').strip()
    password = body.get('password', '')

    if not email or not password:
        return JsonResponse({'message': 'Credenciais inválidas. Verifique e-mail e senha.'}, status=400)

    # Tenta autenticar pelo email diretamente como username
    user = authenticate(request, username=email, password=password)

    # Fallback: busca pelo campo email e autentica pelo username real
    if not user:
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(request, username=user_obj.username, password=password)
        except User.DoesNotExist:
            pass

    if not user:
        return JsonResponse({'message': 'Credenciais inválidas. Verifique e-mail e senha.'}, status=401)

    if not user.is_active:
        return JsonResponse({'message': 'Usuário inativo. Contate o administrador.'}, status=403)

    # Gera os tokens
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    # Monta payload público (sem o token!)
    user_data = {
        'id': str(user.id),
        'username': user.username,
        'email': user.email,
        'name': f"{user.first_name} {user.last_name}".strip() or user.username,
        'role': 'admin' if user.is_staff else 'user',
        'avatar': '',
        'tenant': user.tenant.name if user.tenant else None,
    }

    response = JsonResponse({'user': user_data})

    # Seta os tokens como cookies HttpOnly (inacessíveis ao JavaScript)
    response.set_cookie('access_token', access_token, **_cookie_kwargs(ACCESS_MAX_AGE))
    response.set_cookie('refresh_token', refresh_token, **_cookie_kwargs(REFRESH_MAX_AGE))

    return response


@csrf_exempt
@require_POST
def cookie_logout(request):
    """Invalida a sessão limpando os cookies de autenticação."""
    response = JsonResponse({'message': 'Logout realizado com sucesso.'})
    _delete_auth_cookies(response)
    return response
