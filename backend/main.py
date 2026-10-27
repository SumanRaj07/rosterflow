"""Vercel entrypoint: re-export the FastAPI app.

Local dev and other hosts keep using `uvicorn app.main:app` from backend/;
Vercel's fastapi service looks for an `app` object in a root-level main.py,
so this file just re-exports it.
"""
from app.main import app

__all__ = ["app"]
