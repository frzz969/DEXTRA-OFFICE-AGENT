from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..core.config import get_settings


class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            request.state.tenant_id = None
            request.state.legacy_tenant_slug = get_settings().legacy_tenant_slug
        except Exception:
            try:
                request.state.tenant_id = None
                request.state.legacy_tenant_slug = None
            except Exception:
                pass
        return await call_next(request)