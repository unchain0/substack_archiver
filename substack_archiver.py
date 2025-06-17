import asyncio
import json
import os
import re
import sys
from typing import Any
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv
from playwright.async_api import Page, async_playwright

from colors import log, welcome_message

load_dotenv("config.env")
request_posts = list[list[dict[str, Any]]]


def command_line_parser() -> tuple[str, str]:
    if len(sys.argv) != 3:
        log("""Usage: python3 substack_archiver.py "SUBSSTACKNAME" "URL", """, "white")
        log(
            """Example: python3 substack_archiver.py "abc" "https://abc.substack.com/" or with custom domain: "name123" "https://abc.com/" """,
            "white",
        )
        print("")
        sys.exit(1)
    else:
        return sys.argv[1], sys.argv[2]


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
        self.base_url = base_url[:-1] if base_url.endswith("/") else base_url
        self.post_url = f"{self.base_url}/api/v1/posts?limit=50&offset="
        self.html_path = f"html_dumps/{substack_handle}"
        self.json_path = f"json_dumps/{substack_handle}"

        os.makedirs(self.html_path, exist_ok=True)
        os.makedirs(self.json_path, exist_ok=True)

    async def get_posts(self, page: Page) -> request_posts:
        post_requests = []
        for i in range(0, 500, 50):
            post_url = f"{self.post_url}{i}"
            await page.goto(post_url)
            await page.content()
            try:
                posts = json.loads(await page.evaluate("() => document.body.innerText"))
                if not posts:
                    break
                post_requests.append(posts)
            except json.JSONDecodeError:
                log(f"Error parsing JSON at offset {i}", "red")
                break
            await asyncio.sleep(2)
        return post_requests

    def dump_to_json(self, post_requests: request_posts) -> None:
        for i, posts in enumerate(post_requests):
            with open(f"{self.json_path}/dump{i}.json", "w") as f:
                json.dump(posts, f)

    @staticmethod
    def serialize(value: str) -> str:
        if not isinstance(value, str):
            log(f"Error serializing: {value} is not a string", "red")

        value = re.sub(r"[^\w\s-]", "", value)
        return re.sub(r"[-\s]+", "-", value).strip("-")

    @staticmethod
    def _process_posts(post_requests: request_posts) -> ProcessedPosts:
        processed = ProcessedPosts.create_empty()
        total_posts = 0

        for posts in post_requests:
            if not isinstance(posts, list):
                log("Warning: Expected a list of posts but got something else", "yellow")
                continue

            log(f"Processing batch with {len(posts)} posts", "white")
            total_posts += len(posts)

            for post_data in posts:
                try:
                    if not isinstance(post_data, dict):
                        log("Skipping invalid post (not a dictionary)", "yellow")
                        continue

                    if "title" not in post_data or not post_data["title"]:
                        log("Skipping post without title", "yellow")
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
                        log(f"Post without body: {post.title}", "yellow")
                    else:
                        processed.bodies.append(post.body_html)
                except Exception as e:
                    log(f"Error processing post: {str(e)}", "red")

        log(f"Total posts processed: {total_posts}", "green")
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
            log(f"Error parsing date format: {e}", "yellow")
            return f'<div class="post-date">{date}</div>'

    @staticmethod
    def _format_audio_html(audio: str) -> str:
        return f'<p>Audio link: <a href="{audio}">Listen to audio</a></p>' if audio else ""

    def parse_to_html(self, post_requests: list[Any]) -> tuple[list[str], list[str], list[str]]:
        log("Parsing posts to HTML...", "white")

        processed_posts = self._process_posts(post_requests)
        posts_to_render = self._prepare_posts_for_rendering(processed_posts)

        log(f"Rendering {len(posts_to_render)} HTML files...", "white")

        css_style = self._get_css_style()

        for post in posts_to_render:
            date_html = self._format_date_html(post.date)
            audio_html = self._format_audio_html(post.audio)
            html_template = self._create_html_template(post.to_dict(), css_style, date_html, audio_html)
            self._save_html_file(post.title, html_template)

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

    def _save_html_file(self, title: str, html_content: str) -> None:
        file_name = self.serialize(title)
        file_path = f"{self.html_path}/{file_name}.html"

        if not os.path.isfile(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            log(f"Created: {file_name}.html", "green")
        else:
            log(f"Skipped existing: {file_name}.html", "yellow")


async def main() -> None:
    welcome_message()

    substack_handle, base_url = command_line_parser()
    handler = SubstackPlaywrightHandler(substack_handle, base_url)
    log("Started scraping process, please wait...", "red")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = await context.new_page()

        await page.set_extra_http_headers({
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": handler.base_url,
            "X-Requested-With": "XMLHttpRequest",
        })

        page.on("console", lambda msg: log(f"Browser console: {msg.text}", "yellow") if msg.type == "error" else None)
        page.on("pageerror", lambda err: log(f"Page error: {err}", "red"))

        log("Browser configured, starting to fetch posts...", "white")
        post_requests = await handler.get_posts(page)

        html_result = ([], [], [])

        if not post_requests or len(post_requests) == 0:
            log("No posts were retrieved. Check if the Substack URL is correct.", "red")
        else:
            log(f"Successfully retrieved {len(post_requests)} batches of posts", "green")
            handler.dump_to_json(post_requests)
            html_result = handler.parse_to_html(post_requests)

        await browser.close()

    log(f"Number of downloaded posts: {len(html_result[1])}", "green")
    log(f"Number of posts without body: {len(html_result[0])}", "red")

    if html_result[0]:
        log(f"Number of Inaccessible Posts: {len(html_result[0])}", "red")
        log(
            "Some posts might be inaccessible. Check if you have the necessary permissions.",
            "yellow",
        )

    print("")
    log("Done!", "green", "bold")
    print("")


if __name__ == "__main__":
    asyncio.run(main())
