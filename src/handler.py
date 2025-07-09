import asyncio
import json
import os
from typing import Any

import html2text
from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import Page
from tqdm.asyncio import tqdm

from src.utils import serialize, get_css_style, format_date_html, format_audio_html
from src.models import Post, ProcessedPosts

request_posts = list[list[dict[str, Any]]]


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
                            serialized_title = serialize(post_data.get("title", ""))
                            html_file_name = f"{serialized_title}.html"

                            if html_file_name in self.existing_html_files:
                                logger.debug(f"Skipping already downloaded post: {post_data.get('title')}")
                                current_batch_posts.append(post_data)
                            else:
                                try:
                                    await page.goto(
                                        post_url, wait_until="domcontentloaded", timeout=90000
                                    )
                                except Exception as nav_e:
                                    if "ERR_ABORTED" in str(nav_e):
                                        logger.info(
                                            f"Skipping inaccessible (likely paywalled) post: {post_data.get('title', 'Untitled Post')}"
                                        )
                                    else:
                                        logger.error(f"Navigation to {post_url} failed: {nav_e}")
                                    continue

                                full_html = await page.content()
                                soup = BeautifulSoup(full_html, "html.parser")
                                main_content_div = (
                                    soup.find("div", class_="post-content")
                                    or soup.find("article", class_="post")
                                    or soup.find("div", class_="body")
                                )

                                post = Post.from_dict(post_data)

                                css_style = get_css_style()
                                date_html = format_date_html(post.post_date)
                                audio_html = format_audio_html(post.audio_url)

                                if main_content_div:
                                    post_data["body_html"] = str(main_content_div)

                                    temp_post_for_rendering = {
                                        "title": post.title,
                                        "body": post.body_html,
                                        "description": post.description,
                                        "audio": post.audio_url,
                                        "date": post.post_date,
                                    }

                                    html_template = self._create_html_template(
                                        temp_post_for_rendering, css_style, date_html, audio_html
                                    )
                                    saved_file_path = self._save_html_file(post.title, html_template)

                                    if saved_file_path:
                                        await self._convert_single_html_to_text(saved_file_path)

                                    current_batch_posts.append(post_data)
                                else:
                                    logger.debug(
                                        f"Could not find main content for post: {post_data.get('title', 'Untitled')}. HTML snippet: {full_html[:500]}..."
                                    )
                                    current_batch_posts.append(post_data)

                        pbar.update(1)
                    all_batches_data.append(current_batch_posts)

                    offset += 50
                    await asyncio.sleep(2)
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

    def _process_posts(self, post_requests: list[Any]) -> ProcessedPosts:
        body_none: list[str] = []
        titles: list[str] = []
        bodies: list[str] = []
        descriptions: list[str] = []
        audio_files: list[str] = []
        post_dates: list[str] = []

        for batch in post_requests:
            for post_data in batch:
                post = Post.from_dict(post_data)
                if post.body_html is None:
                    body_none.append(post.title)
                else:
                    bodies.append(post.body_html)
                titles.append(post.title)
                if post.description:
                    descriptions.append(post.description)
                if post.audio_url:
                    audio_files.append(post.audio_url)
                if post.post_date:
                    post_dates.append(post.post_date)

        return ProcessedPosts(
            titles=titles,
            bodies=bodies,
            descriptions=descriptions,
            body_none=body_none,
            audio_files=audio_files,
            post_dates=post_dates,
        )

    async def parse_to_html(self, post_requests: list[Any]) -> tuple[list[str], list[str], list[str]]:
        processed_posts = self._process_posts(post_requests)
        return processed_posts.body_none, processed_posts.titles, processed_posts.audio_files

    def _create_html_template(self, post: dict, css_style: str, date_html: str, audio_html: str) -> str:
        return f'''<!DOCTYPE html>
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
</html>'''

    def _save_html_file(self, title: str, html_content: str) -> str | None:
        file_name = serialize(title)
        file_path = f"{self.html_path}/{file_name}.html"

        if not os.path.isfile(file_path):
            logger.debug(f"Attempting to save HTML file: {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.existing_html_files.add(file_name + ".html")
            logger.debug(f"Successfully saved HTML file: {file_path}")
            return file_path
        else:
            logger.debug(f"HTML file already exists, skipping: {file_path}")
            return None

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

