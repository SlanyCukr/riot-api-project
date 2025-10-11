"""Application entry point for the Riot API Backend."""

import uvicorn
from app.config import get_global_settings

if __name__ == "__main__":
    settings = get_global_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
