"""
Start Continue.dev Server

Run with:
    python run_server.py
    
Or with configuration:
    python run_server.py --host 0.0.0.0 --port 8000 --env production
"""

import argparse
import logging
from pathlib import Path

from core.chat_interface import ContinueDEVServer
from core.server_config import ServerConfig, ACTIVE_CONFIG
from core.structured_logger import StructuredLogger


def main():
    """Start the server."""
    
    parser = argparse.ArgumentParser(
        description="Start Continue.dev integration server"
    )
    parser.add_argument("--host", default=ACTIVE_CONFIG.host, help="Server host")
    parser.add_argument("--port", type=int, default=ACTIVE_CONFIG.port, help="Server port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument(
        "--env",
        choices=["development", "production"],
        default="development",
        help="Environment"
    )
    parser.add_argument("--config", type=Path, help="Config file path")
    
    args = parser.parse_args()
    
    # Load config
    if args.config:
        config = ServerConfig.from_file(args.config)
    else:
        config = ACTIVE_CONFIG
    
    # Override with CLI args if provided
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.reload:
        config.reload = True
    config.log_level = "DEBUG" if args.env == "development" else "WARNING"
    
    # Setup logging
    StructuredLogger(
        log_dir=config.log_dir,
        level=logging.DEBUG if args.env == "development" else logging.INFO,
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("Continue.dev Integration Server")
    logger.info("=" * 60)
    logger.info(f"Environment: {args.env}")
    logger.info(f"Host: {config.host}")
    logger.info(f"Port: {config.port}")
    logger.info(f"Auth: {'enabled' if config.enable_auth else 'disabled'}")
    logger.info(f"Redis: {'enabled' if config.enable_redis else 'disabled'}")
    logger.info(f"Tracing: {'enabled' if config.enable_tracing else 'disabled'}")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Server starting...")
    logger.info(f"API available at http://{config.host}:{config.port}/api/v1")
    logger.info(f"Docs at http://{config.host}:{config.port}/docs")
    logger.info("")
    
    # Create and run server
    try:
        server = ContinueDEVServer(
            host=config.host,
            port=config.port,
            secret_key=config.secret_key,
            enable_auth=config.enable_auth,
            enable_redis=config.enable_redis,
        )
        
        server.run(reload=config.reload)
    
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main()
