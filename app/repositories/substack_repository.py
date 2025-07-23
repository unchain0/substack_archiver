import json
from pathlib import Path

from loguru import logger
from playwright.async_api import Browser, Page
from rich.progress import Progress


class SubstackRepository:
    def __init__(self, base_url: str, browser: Browser) -> None:
        if base_url.endswith("/archive") or base_url.endswith("/archive/"):
            self.base_url = base_url.replace("/archive", "")
        else:
            self.base_url = base_url[:-1] if base_url.endswith("/") else base_url
        self.browser = browser

    async def get_page(self) -> Page:
        context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36)",
            "locale": "en-US",
        }

        storage_state_path = Path("storage_state.json")
        if storage_state_path.exists():
            logger.debug("Loading session from storage_state.json")
            context = await self.browser.new_context(
                storage_state=str(storage_state_path),
                user_agent=context_options["user_agent"],
                locale=context_options["locale"],
            )
            page = await context.new_page()
            logger.debug("Session loaded. Skipping direct login attempt.")
        else:
            logger.warning("storage_state.json not found. Attempting direct login if credentials are set.")
            context = await self.browser.new_context(
                user_agent=context_options["user_agent"], locale=context_options["locale"]
            )
            page = await context.new_page()

            await page.set_extra_http_headers({
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": self.base_url,
                "X-Requested-With": "XMLHttpRequest",
            })

            page.on(
                "console", lambda msg: logger.warning(f"Browser console: {msg.text}") if msg.type == "error" else None
            )
            page.on("pageerror", lambda err: logger.error(f"Page error: {err}"))

            logger.warning("No storage_state.json found. Proceeding without login.")
        return page

    async def get_posts(self, page: Page, progress: Progress, task_id) -> list[dict]:
        all_posts_data: list[dict] = []
        offset = 0

        logger.debug("Fetching posts from Substack API...")

        while True:
            api_url = f"{self.base_url}/api/v1/posts?limit=50&offset={offset}"
            logger.debug(f"Fetching API URL: {api_url}")
            await page.goto(api_url)
            try:
                api_response = json.loads(await page.evaluate("() => document.body.innerText"))
                if not api_response:
                    break

                all_posts_data.extend(api_response)
                progress.update(task_id, advance=len(api_response))

                offset += 50
            except json.JSONDecodeError:
                logger.error(f"Error parsing JSON from API at offset {offset}")
                break
            except Exception as e:
                logger.error(f"An error occurred while processing posts: {e}")
                break
        return all_posts_data
