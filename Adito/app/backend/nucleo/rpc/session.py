"""Usuário local e tenant do desktop (um só por instalação), carregados uma vez."""
from __future__ import annotations

from core.records import Tenant, User, get_local_user, tenant_of

_user: User | None = None
_tenant: Tenant | None = None


def current() -> tuple[User, Tenant | None]:
    global _user, _tenant
    if _user is None:
        _user = get_local_user()
        _tenant = tenant_of(_user)
    return _user, _tenant


def reset() -> None:
    global _user, _tenant
    _user = _tenant = None
