import asyncio
import os
import sys

from loguru import logger
from playwright.async_api import async_playwright

from src.config import load_config
from src.handler import SubstackPlaywrightHandler
from src.utils import TruncatingFileSink


async def main() -> None:
    logger.remove()
    logger.add(TruncatingFileSink("debug.log", 10 * 1024 * 1024), level="DEBUG")
    logger.add(TruncatingFileSink("debug.log", 10 * 1024 * 1024), level="DEBUG")
    logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {message}", colorize=True)
    logger.info("Welcome to Substack Archiver!")

    substacks_to_process = load_config()

    if not substacks_to_process:
        logger.info("No substacks found in config.json. Exiting.")
        sys.exit(0)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for substack_config in substacks_to_process:
            substack_handle = substack_config.get("name")
            base_url = substack_config.get("url")

            if not substack_handle or not base_url:
                logger.warning(f"Skipping invalid substack entry: {substack_config}")
                continue

            logger.info(f"--- Starting processing for {substack_handle} ({base_url}) ---")
            handler = SubstackPlaywrightHandler(substack_handle, base_url)
            logger.info("Started scraping process, please wait...")
            context_options = {
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36)",
                "locale": "en-US",
            }

            if os.path.exists("storage_state.json"):
                logger.info("Loading session from storage_state.json")
                context = await browser.new_context(
                    storage_state="storage_state.json",
                    user_agent=context_options["user_agent"],
                    locale=context_options["locale"],
                )
                page = await context.new_page()
                logger.success("Session loaded. Skipping direct login attempt.")
            else:
                logger.warning("storage_state.json not found. Attempting direct login if credentials are set.")
                context = await browser.new_context(
                    user_agent=context_options["user_agent"], locale=context_options["locale"]
                )
                page = await context.new_page()

                await page.set_extra_http_headers({
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": handler.base_url,
                    "X-Requested-With": "XMLHttpRequest",
                })

                page.on(
                    "console", lambda msg: logger.warning(f"Browser console: {msg.text}") if msg.type == "error" else None
                )
                page.on("pageerror", lambda err: logger.error(f"Page error: {err}"))

                if os.getenv("SUBSTACK_EMAIL") and os.getenv("SUBSTACK_PASSWORD"):
                    login_successful = await handler.login(page)
                    if not login_successful:
                        logger.error("Login failed for this substack. Skipping to next.")
                        continue # Skip to the next substack
                    else:
                        logger.success("Login reported as successful.")
                else:
                    logger.warning(
                        "No login credentials found in .env and no storage_state.json. Proceeding without login."
                    )

            # Set headers for the page regardless of login method
            await page.set_extra_http_headers({
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": handler.base_url,
                "X-Requested-With": "XMLHttpRequest",
            })

            logger.info("Browser configured, starting to fetch posts...")
            post_requests = await handler.get_posts(page)

            html_result: tuple[list[str], list[str], list[str>] = ([], [], [])

            if not post_requests or len(post_requests) == 0:
                logger.error("No posts were retrieved. Check if the Substack URL is correct.")
            else:
                logger.success(f"Successfully retrieved {len(post_requests)} batches of posts")
                handler.dump_to_json(post_requests)
                html_result = await handler.parse_to_html(post_requests)

            logger.success(f"Number of downloaded posts: {len(html_result[1])}")
            logger.error(f"Number of posts without body: {len(html_result[0])}")

            if html_result[0]:
                logger.error(f"Number of Inaccessible Posts: {len(html_result[0])}")
                logger.warning("Some posts might be inaccessible. Check if you have the necessary permissions.")

            logger.success("Done for this substack!")

        await browser.close()
    logger.success("All substacks processed!")
    print("")


if __name__ == "__main__":
    asyncio.run(main())