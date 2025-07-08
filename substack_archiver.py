import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import html2text
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from loguru import logger
from playwright.async_api import Page, async_playwright
from tqdm.asyncio import tqdm

load_dotenv(".env")
request_posts = list[list[dict[str, Any]]]


def load_config(config_path: str = "config.json") -> list[dict[str, str]]:
    if not os.path.exists(config_path):
        logger.error(f"Config file not found at {config_path}")
        sys.exit(1)
    with open(config_path, "r") as f:
        config = json.load(f)
    return config.get("substacks", [])


@dataclass
class Post:
    title: str
    body_html: str | None
    description: str = ""
    podcast_url: str = ""
    post_date: str = ""


@dataclass
class ProcessedPosts:
    titles: list[str]
    bodies: list[str]
    descriptions: list[str]
    body_none: list[str]
    audio_files: list[str]
    post_dates: list[str]

    @classmethod
    def create_empty(cls) -> "ProcessedPosts":
        return cls([], [], [], [], [], [])


@dataclass
class PostForRendering:
    title: str
    body: str
    description: str
    audio: str
    date: str

    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "body": self.body,
            "description": self.description,
            "audio": self.audio,
            "date": self.date,
        }


class SubstackPlaywrightHandler:
    def __init__(self, substack_handle: str, base_url: str) -> None:
        self.substack_handle = substack_handle
        if base_url.endswith("/archive") or base_url.endswith("/archive/"):
            self.base_url = base_url.replace("/archive", "")
        else:
            self.base_url = base_url[:-1] if base_url.endswith("/") else base_url
        self.post_url = f"{self.base_url}/api/v1/posts?limit=50&offset="
        self.html_path = f"html_dumps/{substack_handle}"
        self.json_path = f"json_dumps/{substack_handle}"
        self.text_path = f"text_dumps/{substack_handle}"
        self.existing_html_files: set[str] = set()

        os.makedirs(self.html_path, exist_ok=True)
        os.makedirs(self.json_path, exist_ok=True)
        os.makedirs(self.text_path, exist_ok=True)
        self._load_existing_html_files()

    def _load_existing_html_files(self) -> None:
        logger.info(f"Checking for existing HTML files in {self.html_path}...")
        if os.path.exists(self.html_path):
            self.existing_html_files = {f for f in os.listdir(self.html_path) if f.endswith(".html")}
        logger.info(f"Found {len(self.existing_html_files)} existing HTML files.")

    async def login(self, page: Page) -> bool:
        email = os.getenv("SUBSTACK_EMAIL")
        password = os.getenv("SUBSTACK_PASSWORD")

        if not email or not password:
            logger.warning("SUBSTACK_EMAIL or SUBSTACK_PASSWORD not set in .env. Skipping login.")
            return False

        logger.info("Attempting to log in...")
        login_url = f"{self.base_url}/account/login"
        await page.goto(login_url)

        try:
            logger.info("Filling email...")
            await page.fill("input[name='email']", email)
            logger.info("Clicking first continue button...")
            await page.click("button[type='submit']")

            logger.info("Waiting for password field...")
            await page.wait_for_selector("input[name='password']", timeout=30000)
            logger.info("Filling password...")
            await page.fill("input[name='password']", password)
            logger.info("Clicking second continue button...")
            await page.click("button[type='submit']")

            logger.info("Waiting for successful login indicator...")
            await page.wait_for_selector('a[href*="/account"]', timeout=30000)
            logger.success("Login successful!")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    async def get_posts(self, page: Page) -> request_posts:
        all_batches_data = []
        offset = 0

        logger.info("Fetching posts from Substack API...")

        with tqdm(desc="Fetching posts", unit="post") as pbar:
            while True:
                api_url = f"{self.base_url}/api/v1/posts?limit=50&offset={offset}"
                logger.debug(f"Fetching API URL: {api_url}")
                await page.goto(api_url)
                try:
                    api_response = json.loads(await page.evaluate("() => document.body.innerText"))
                    logger.debug(f"API Response Type: {type(api_response)}, Snippet: {str(api_response)[:200]}")
                    if not api_response:
                        break

                    current_batch_posts = []
                    for post_data in api_response:
                        logger.debug(f"Processing post: Title='{post_data.get("title", "N/A")}', URL='{post_data.get("canonical_url", "N/A")}'")
                        if post_data.get("slug"):
                            post_url = f"{self.base_url}/p/{post_data["slug"]}"
                            serialized_title = self.serialize(post_data.get("title", ""))
                            html_file_name = f"{serialized_title}.html"

                            if html_file_name in self.existing_html_files:
                                logger.debug(f"Skipping already downloaded post: {post_data.get('title')}")
                                # Add to current_batch_posts but without fetching body_html again
                                # The existing file will be picked up by parse_to_html later
                                current_batch_posts.append(post_data)
                            else:
                                try:
                                    await page.goto(
                                        post_url, wait_until="domcontentloaded", timeout=90000
                                    )  # Increased timeout to 90 seconds
                                except Exception as nav_e:
                                    if "ERR_ABORTED" in str(nav_e):
                                        logger.info(
                                            f"Skipping inaccessible (likely paywalled) post: {post_data.get('title', 'Untitled Post')}"
                                        )
                                    else:
                                        logger.error(f"Navigation to {post_url} failed: {nav_e}")
                                    continue  # Skip to the next post if navigation fails

                                full_html = await page.content()

                                soup = BeautifulSoup(full_html, "html.parser")
                                main_content_div = (
                                    soup.find("div", class_="post-content")
                                    or soup.find("article", class_="post")
                                    or soup.find("div", class_="body")
                                )

                                if main_content_div:
                                    post_data["body_html"] = str(main_content_div)

                                    # New logic to save HTML and convert to text immediately
                                    post_title = post_data.get("title", "Untitled Post")
                                    post_description = post_data.get("description", "")
                                    post_audio = post_data.get("podcast_url", "")
                                    post_date = post_data.get("post_date", "")

                                    # Create a temporary PostForRendering-like dict for _create_html_template
                                    temp_post_for_rendering = {
                                        "title": post_title,
                                        "body": post_data["body_html"],  # Use the extracted body_html
                                        "description": post_description,
                                        "audio": post_audio,
                                        "date": post_date,
                                    }

                                    css_style = self._get_css_style()
                                    date_html = self._format_date_html(post_date)
                                    audio_html = self._format_audio_html(post_audio)

                                    html_template = self._create_html_template(
                                        temp_post_for_rendering, css_style, date_html, audio_html
                                    )
                                    saved_file_path = self._save_html_file(post_title, html_template)

                                    if saved_file_path:
                                        await self._convert_single_html_to_text(saved_file_path)

                                    current_batch_posts.append(post_data)
                                else:
                                    logger.debug(
                                        f"Could not find main content for post: {post_data.get('title', 'Untitled')}. HTML snippet: {full_html[:500]}..."
                                    )
                                    current_batch_posts.append(post_data)
                                    current_batch_posts.append(post_data) # Append even if main content not found

                        pbar.update(1)
                    all_batches_data.append(current_batch_posts)

                    offset += 50
                    await asyncio.sleep(2)  # Be polite and avoid hammering the server
                except json.JSONDecodeError:
                    logger.error(f"Error parsing JSON from API at offset {offset}")
                    break
                except Exception as e:
                    logger.error(f"An error occurred while processing posts: {e}")
                    break
        return all_batches_data

    def dump_to_json(self, post_requests: request_posts) -> None:
        for i, posts in enumerate(post_requests):
            with open(f"{self.json_path}/dump{i}.json", "w") as f:
                json.dump(posts, f)

    @staticmethod
    def serialize(value: str) -> str:
        if not isinstance(value, str):
            logger.error(f"Error serializing: {value} is not a string")

        value = re.sub(r"[^\w\s-]", "", value)
        return re.sub(r"[-\s]+", "-", value).strip("-")

    @staticmethod
    def _process_posts(post_requests: request_posts) -> ProcessedPosts:
        processed = ProcessedPosts.create_empty()
        total_posts = 0

        for posts in post_requests:
            if not isinstance(posts, list):
                logger.warning("Warning: Expected a list of posts but got something else")
                continue

            total_posts += len(posts)

            for post_data in posts:
                try:
                    if not isinstance(post_data, dict):
                        logger.warning("Skipping invalid post (not a dictionary)")
                        continue

                    if "title" not in post_data or not post_data["title"]:
                        logger.warning("Skipping post without title")
                        continue

                    post = Post(
                        title=post_data.get("title", "Untitled Post"),
                        body_html=post_data.get("body_html"),
                        description=post_data.get("description", ""),
                        podcast_url=post_data.get("podcast_url", ""),
                        post_date=post_data.get("post_date", ""),
                    )

                    processed.titles.append(post.title)
                    processed.descriptions.append(post.description)
                    processed.audio_files.append(post.podcast_url)
                    processed.post_dates.append(post.post_date)

                    if post.body_html is None:
                        processed.body_none.append(post.title)
                        logger.debug(f"Post without body: {post.title}")
                        processed.bodies.append("")  # Add empty string for missing body
                    else:
                        processed.bodies.append(post.body_html)
                except Exception as e:
                    logger.error(f"Error processing post: {str(e)}")

        logger.success(f"Total posts processed: {total_posts}")
        return processed

    @staticmethod
    def _prepare_posts_for_rendering(processed: ProcessedPosts) -> list[PostForRendering]:
        posts_to_render: list[PostForRendering] = []

        for title, body, description, audio, date in zip(
            processed.titles,
            processed.bodies,
            processed.descriptions,
            processed.audio_files,
            processed.post_dates,
        ):
            if body is None:
                continue

            posts_to_render.append(
                PostForRendering(title=title, body=body, description=description, audio=audio, date=date)
            )
        return posts_to_render

    @staticmethod
    def _get_css_style() -> str:
        return """
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            h1 { font-size: 2.2em; margin-bottom: 0.5em; }
            .post-meta { color: #666; font-size: 0.9em; margin-bottom: 2em; }
            .post-content { margin-top: 2em; }
            .post-content img { max-width: 100%; height: auto; }
            blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 20px; color: #555; }
            pre { background: #f6f8fa; padding: 16px; overflow: auto; border-radius: 3px; }
            code { font-family: monospace; background: #f6f8fa; padding: 2px 4px; border-radius: 3px; }
        </style>
        """

    @staticmethod
    def _format_date_html(date: str) -> str:
        if not date:
            return ""

        try:
            date_obj = datetime.fromisoformat(date.replace("Z", "+00:00"))
            formatted_date = date_obj.strftime("%B %d, %Y")
            return f'<div class="post-date">{formatted_date}</div>'
        except ValueError as e:
            logger.warning(f"Error parsing date format: {e}")
            return f'<div class="post-date">{date}</div>'

    @staticmethod
    def _format_audio_html(audio: str) -> str:
        return f'<p>Audio link: <a href="{audio}">Listen to audio</a></p>' if audio else ""

    async def parse_to_html(self, post_requests: list[Any]) -> tuple[list[str], list[str], list[str]]:
        processed_posts = self._process_posts(post_requests)

        return processed_posts.body_none, processed_posts.titles, processed_posts.audio_files

    def _create_html_template(self, post: dict, css_style: str, date_html: str, audio_html: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{post["title"]}</title>
    {css_style}
</head>
<body>
    <article>
        <header>
            <h1>{post["title"]}</h1>
            <div class="post-meta">
                {date_html}
                <div class="post-description">{post["description"]}</div>
                {audio_html}
            </div>
        </header>
        <div class="post-content">{post["body"]}</div>
    </article>
    <footer>
        <p>Archived from {self.base_url}</p>
    </footer>
</body>
</html>"""

    def _save_html_file(self, title: str, html_content: str) -> str | None:
        file_name = self.serialize(title)
        file_path = f"{self.html_path}/{file_name}.html"

        if not os.path.isfile(file_path):
            logger.debug(f"Attempting to save HTML file: {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.existing_html_files.add(file_name + ".html")  # Add to the set of existing files
            logger.debug(f"Successfully saved HTML file: {file_path}")
            return file_path  # Return the path for conversion
        else:
            logger.debug(f"HTML file already exists, skipping: {file_path}")
            return None  # Indicate no new file was created

    async def _convert_single_html_to_text(self, html_file_path: str) -> None:
        loop = asyncio.get_running_loop()
        relative_path = os.path.relpath(html_file_path, self.html_path)
        text_file_path = os.path.join(self.text_path, relative_path.replace(".html", ".txt"))

        os.makedirs(os.path.dirname(text_file_path), exist_ok=True)

        def _sync_convert():
            with open(html_file_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return html2text.html2text(html_content)

        text_content = await loop.run_in_executor(None, _sync_convert)

        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(text_content)

    def _clean_html_for_text_conversion(self, html_content: str) -> str:
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove social sharing buttons and related elements
        for div in soup.find_all("div", class_=["modal", "post-ufi", "pencraft pc-display-flex pc-flexDirection-column pc-gap-24 pc-padding-24 pc-reset bg-primary-zk6FDl border-detail-EGrm7T pc-borderRadius-md container-xiJVit"]):
            div.decompose()

        # Remove subscription prompts
        for div in soup.find_all("div", class_="pencraft pc-display-flex pc-flexDirection-column pc-gap-20 pc-reset"):
            div.decompose()
        for div in soup.find_all("div", class_="subscribe-widget"):
            div.decompose()
        for ul in soup.find_all("ul", class_="dropdown-menu tooltip subscribe-prompt-dropdown free"):
            ul.decompose()

        # Remove image containers (if they add noise)
        for div in soup.find_all("div", class_="captioned-image-container"):
            div.decompose()

        # Remove empty header anchors
        for h in soup.find_all(class_="header-anchor-post"):
            if not h.get_text(strip=True):
                h.decompose()

        # Remove empty divs and dividers
        for div in soup.find_all("div", class_="visibility-check"):
            div.decompose()
        for div in soup.find_all("div", class_="divider-Ti4OTa"):
            div.decompose()

        # Remove footer
        footer = soup.find("footer")
        if footer:
            footer.decompose()
            
        # Remove any remaining script and style tags
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        return str(soup)


class TruncatingFileSink:
    def __init__(self, file_path, max_size_bytes):
        self.file_path = file_path
        self.max_size_bytes = max_size_bytes
        self.file = open(file_path, "a", encoding="utf-8")

    def write(self, message):
        if self.file.tell() + len(message) > self.max_size_bytes:
            self.file.seek(0)
            self.file.truncate(0)
            
        self.file.write(message)
        self.file.flush()

    def __call__(self, message):
        self.write(message)

    def __del__(self):
        if hasattr(self, 'file') and not self.file.closed:
            self.file.close()


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
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
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

            html_result: tuple[list[str], list[str], list[str]] = ([], [], [])

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
