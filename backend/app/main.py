from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routers import auth, letterboxd_import, library, movies
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Movie Explorer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret, same_site="lax")

app.include_router(auth.router)
app.include_router(movies.router)
app.include_router(library.router)
app.include_router(letterboxd_import.router)


@app.get("/health")
def health():
    return {"status": "ok"}
