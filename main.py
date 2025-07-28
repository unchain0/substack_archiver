import asyncio
import sys

from loguru import logger

from app.api.cli import cli
from app.config import load_config
from app.services.agno_service import AgnoService
from app.utils import TruncatingFileSink


async def main() -> None:
    logger.remove()
    logger.add(TruncatingFileSink("debug.log", 2 * 1024 * 1024), level="DEBUG")
    logger.add(sys.stderr, level="SUCCESS", format="{message}", colorize=True)

    await cli(load_config())

    AgnoService().run()


if __name__ == "__main__":
    asyncio.run(main())
