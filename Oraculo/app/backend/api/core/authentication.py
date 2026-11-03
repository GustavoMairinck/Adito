from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class CookieJWTAuthentication(JWTAuthentication):
    """Lê o JWT de um HttpOnly Cookie em vez do header Authorization.

    O cookie 'access_token' é setado pelo endpoint /api/auth/cookie/login e
    enviado automaticamente pelo browser em todas as requisições.
    """

    def authenticate(self, request):
        # 1. Tenta o cookie primeiro
        raw_token = request.COOKIES.get('access_token')

        if raw_token:
            try:
                validated_token = self.get_validated_token(raw_token)
                return self.get_user(validated_token), validated_token
            except (InvalidToken, TokenError):
                return None

        # 2. Fallback para o header Authorization (compatibilidade com clientes legados)
        return super().authenticate(request)
