from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.core.rate_limit import RateLimiter
from app.routes import auth, backtests, decisions, market

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="QuFin API",
        version="0.1.0",
        description=(
            "Research and decision-support data for FX, metals, energy and crypto. "
            "Not investment advice."
        ),
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )
    app.state.settings = settings
    app.state.auth_limiter = RateLimiter(
        settings.auth_rate_limit, settings.auth_rate_window_seconds
    )

    @app.middleware("http")
    async def reject_cross_site_writes(request: Request, call_next):
        # CSRF defence in depth on top of SameSite=Lax cookies and the CORS preflight:
        # a browser always sends Origin on cross-origin writes, so refuse unknown ones.
        origin = request.headers.get("origin")
        if (
            request.method in UNSAFE_METHODS
            and origin is not None
            and origin not in settings.cors_origins
        ):
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
        return await call_next(request)

    # Added after the origin check, so it wraps it and the 403s carry CORS headers too.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth.router)
    app.include_router(market.router)
    app.include_router(backtests.router)
    app.include_router(decisions.router)
    return app


app = create_app()
