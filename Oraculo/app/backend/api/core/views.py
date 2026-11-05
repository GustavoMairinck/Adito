import os

import httpx
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Contexto

MISTRAL_MODELS_URL = "https://api.mistral.ai/v1/models"
LLM_KEY_MISSING = "Configure a chave da Mistral em Configurações para usar o chat."


def llm_configured() -> bool:
    """A chave chega do cofre do SO via ambiente quando o Tauri sobe o backend."""
    return bool(os.environ.get("MISTRAL_API_KEY"))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Usuário local do desktop, no mesmo formato que o front recebia do login."""
    user = request.user
    return Response({
        'id': str(user.id),
        'username': user.username,
        'email': user.email,
        'name': f"{user.first_name} {user.last_name}".strip() or 'Usuário local',
        'role': 'admin' if user.is_staff else 'user',
        'avatar': '',
        'tenant': user.tenant.name if user.tenant else None,
        'llm_configured': llm_configured(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_llm_key(request):
    """Testa uma chave da Mistral antes de o Tauri guardá-la no cofre. A chave não é gravada aqui."""
    key = (request.data.get('key') or '').strip()
    if not key:
        return Response({"ok": False, "reason": "Informe a chave."}, status=400)
    try:
        resp = httpx.get(MISTRAL_MODELS_URL, headers={"Authorization": f"Bearer {key}"}, timeout=15)
    except httpx.HTTPError:
        return Response({"ok": False, "reason": "Sem conexão com a Mistral. Verifique a internet e tente de novo."})
    if resp.status_code == 200:
        return Response({"ok": True})
    reasons = {
        401: "Chave inválida.",
        403: "Chave sem permissão para a API.",
        429: "Cota da chave esgotada ou limite de uso atingido.",
    }
    return Response({"ok": False, "reason": reasons.get(resp.status_code, f"A Mistral respondeu com erro {resp.status_code}.")})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def contextos(request):
    """Contextos ativos para o seletor do chat e do dashboard (sem colunas sensíveis)."""
    rows = Contexto.objects.filter(tenant=request.user.tenant, is_active=True).order_by('name')
    return Response([
        {
            "id": str(contexto.id),
            "slug": contexto.slug,
            "name": contexto.name,
            "description": contexto.description,
            "views": [
                {"name": view["name"], "description": view.get("description", "")}
                for view in contexto.views
            ],
        }
        for contexto in rows
    ])
