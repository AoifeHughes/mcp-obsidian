#!/usr/bin/env python3
"""
HTTP Server wrapper for MCP Obsidian Server

This script runs the MCP Obsidian server over HTTP with Server-Sent Events (SSE)
instead of stdio. This enables web-based clients and remote access.

Usage:
    uv run mcp-obsidian-http

Environment Variables:
    MCP_HTTP_HOST: Host to bind to (default: 127.0.0.1)
    MCP_HTTP_PORT: Port to bind to (default: 8000)
    OBSIDIAN_API_KEY: Your Obsidian REST API key (required)
    OBSIDIAN_HOST: Obsidian REST API host (default: 127.0.0.1)
    OBSIDIAN_PORT: Obsidian REST API port (default: 27124)
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Import the MCP server instance
from .server import app, logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
http_logger = logging.getLogger("mcp-obsidian-http")

# Server configuration
HOST = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
PORT = int(os.getenv("MCP_HTTP_PORT", "8000"))


async def health_check(request):
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "mcp-obsidian-http",
        "version": "0.2.1"
    })


async def handle_sse(request):
    """Handle SSE connections for MCP"""
    async with SseServerTransport("/messages") as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


async def handle_messages(request):
    """Handle POST requests to /messages endpoint"""
    async with SseServerTransport("/messages") as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


@asynccontextmanager
async def lifespan(app):
    """Lifespan context manager for startup/shutdown events"""
    http_logger.info("=" * 60)
    http_logger.info("🚀 MCP Obsidian HTTP Server Starting")
    http_logger.info("=" * 60)
    http_logger.info(f"📍 Server Address: http://{HOST}:{PORT}")
    http_logger.info(f"🔌 SSE Endpoint: http://{HOST}:{PORT}/sse")
    http_logger.info(f"💬 Messages Endpoint: http://{HOST}:{PORT}/messages")
    http_logger.info(f"❤️  Health Check: http://{HOST}:{PORT}/health")

    # Check required configuration
    if not os.getenv("OBSIDIAN_API_KEY"):
        http_logger.warning("⚠️  OBSIDIAN_API_KEY not set - tools may fail at runtime")
    else:
        http_logger.info("✅ OBSIDIAN_API_KEY configured")

    obsidian_host = os.getenv("OBSIDIAN_HOST", "127.0.0.1")
    obsidian_port = os.getenv("OBSIDIAN_PORT", "27124")
    http_logger.info(f"🗂️  Obsidian API: http://{obsidian_host}:{obsidian_port}")
    http_logger.info("=" * 60)

    yield

    http_logger.info("👋 MCP Obsidian HTTP Server Shutting Down")


# Create Starlette application
routes = [
    Route("/health", health_check, methods=["GET"]),
    Route("/sse", handle_sse, methods=["GET"]),
    Route("/messages", handle_messages, methods=["POST"]),
]

starlette_app = Starlette(
    debug=True,
    routes=routes,
    lifespan=lifespan
)

# Add CORS middleware to allow cross-origin requests
starlette_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def main():
    """Main entry point for HTTP server"""
    import uvicorn

    try:
        uvicorn.run(
            starlette_app,
            host=HOST,
            port=PORT,
            log_level="info"
        )
    except KeyboardInterrupt:
        http_logger.info("\n👋 Server stopped by user")
    except Exception as e:
        http_logger.error(f"❌ Server error: {e}")
        raise


if __name__ == "__main__":
    main()
