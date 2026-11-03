from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Contexto


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
    })


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
