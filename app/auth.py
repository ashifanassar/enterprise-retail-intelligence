from fastapi import Header, HTTPException

from app.config import API_SECRET_KEY


def validate_api_key(x_api_key: str | None = Header(default=None)) -> str:
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
