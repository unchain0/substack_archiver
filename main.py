import argparse
import asyncio
import sys
from argparse import Namespace

from loguru import logger

from app.api.cli import cli
from app.config import load_config
from app.utils import TruncatingFileSink
from scripts.rag import Rag


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser(description="Substack Archiver with RAG capabilities")
    parser.add_argument("--temperature", type=float, default=0, help="Temperature for the LLM (0-1)")
    parser.add_argument("--skip-archive", action="store_true", help="Skip archiving and only run the RAG system")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    logger.remove()
    logger.add(TruncatingFileSink("debug.log", 2 * 1024 * 1024), level="DEBUG")
    logger.add(sys.stderr, level="SUCCESS", format="{message}", colorize=True)

    if not args.skip_archive:
        substacks_to_process = load_config()
        await cli(substacks_to_process)

    Rag.initialize(args.temperature)


if __name__ == "__main__":
    asyncio.run(main())
