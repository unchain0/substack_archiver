import asyncio
import sys

from loguru import logger

from app.api.cli import cli
from app.config import load_config
from app.utils import TruncatingFileSink


async def main() -> None:
    logger.remove()
    logger.add(TruncatingFileSink("debug.log", 2 * 1024 * 1024), level="DEBUG")
    logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}", colorize=True)
    logger.info("Welcome to Substack Archiver!")

    substacks_to_process = load_config()

    if not substacks_to_process:
        logger.info("No substacks found in config.json. Exiting.")
        sys.exit(0)

    await cli(substacks_to_process)

    logger.success("All substacks processed!")
    print("")


if __name__ == "__main__":
    asyncio.run(main())
