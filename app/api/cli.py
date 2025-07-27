import asyncio

from loguru import logger
from playwright.async_api import async_playwright
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn

from app.services.archiver_service import ArchiverService


async def cli(substacks_to_process: list[dict[str, str]]) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed} posts"),
        ) as progress:
            tasks = []
            for i, substack_config in enumerate(substacks_to_process):
                substack_handle = substack_config.get("name")
                base_url = substack_config.get("url")

                if not substack_handle or not base_url:
                    logger.warning(f"Skipping invalid substack entry: {substack_config}")
                    continue

                # Pass the rich progress instance to the service
                output_directory = substack_config.get("output_directory", "./archive")
                skip_existing = bool(substack_config.get("skip_existing", True))

                archiver_service = ArchiverService(
                    substack_handle,
                    base_url,
                    browser,
                    progress,
                    output_directory=output_directory,
                    skip_existing=skip_existing,
                )
                tasks.append(archiver_service.archive())

            await asyncio.gather(*tasks)

        await browser.close()
