"""Run the FastAPI application."""

import uvicorn
import asyncio
import sys
from app.main import app
from app.config import settings


def main():
    """Main entry point."""
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )


if __name__ == "__main__":
    main()
