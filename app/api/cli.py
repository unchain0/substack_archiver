from loguru import logger
from playwright.async_api import async_playwright

from app.services.archiver_service import ArchiverService


async def cli(substacks_to_process: list[dict[str, str]]) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for substack_config in substacks_to_process:
            substack_handle = substack_config.get("name")
            base_url = substack_config.get("url")

            if not substack_handle or not base_url:
                logger.warning(f"Skipping invalid substack entry: {substack_config}")
                continue

            logger.info(f"--- Starting processing for {substack_handle} ({base_url}) ---")
            archiver_service = ArchiverService(substack_handle, base_url, browser)
            await archiver_service.archive()

        await browser.close()
