import asyncio
import sys

from loguru import logger

from app.api.cli import cli
from app.config import load_config
from app.utils import TruncatingFileSink


async def main() -> None:
    logger.remove()
    logger.add(TruncatingFileSink("debug.log", 2 * 1024 * 1024), level="DEBUG")
    logger.add(sys.stderr, level="SUCCESS", format="{message}", colorize=True)

    substacks_to_process = load_config()

    await cli(substacks_to_process)


if __name__ == "__main__":
    asyncio.run(main())
