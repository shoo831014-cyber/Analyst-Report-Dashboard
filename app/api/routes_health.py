from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict[str, str]:
    settings = request.app.state.settings
    return {"status": "ok", "app": settings.app_name}

