import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import html2text
from bs4 import BeautifulSoup, Tag
from loguru import logger

from app.models import Post
from app.utils import serialize


class FileRepository:
    def __init__(self, substack_handle: str, output_directory: str = "./archive") -> None:
        self.substack_handle = substack_handle
        base_path = Path(output_directory) / substack_handle
        self.html_path = base_path / "html_dumps"
        self.json_path = base_path / "json_dumps"
        self.text_path = base_path / "text_dumps"
        self.existing_html_files: set[str] = set()

        self.html_path.mkdir(parents=True, exist_ok=True)
        self.json_path.mkdir(parents=True, exist_ok=True)
        self.text_path.mkdir(parents=True, exist_ok=True)
        self._load_existing_html_files()

    def _load_existing_html_files(self) -> None:
        self.existing_html_files = {file.name for file in self.html_path.glob("*.html")}

    def html_file_exists(self, title: str) -> bool:
        file_name = serialize(title)
        return (self.html_path / f"{file_name}.html").is_file()

    def dump_to_json(self, posts: list[Any]) -> None:
        with open(self.json_path / "dump.json", "w") as f:
            json.dump(posts, f)

    def create_html_template(self, post: Post) -> str:
        css_style = self._get_css_style()
        date_html = self._format_date_html(post.post_date) if post.post_date else ""
        audio_html = self._format_audio_html(post.audio_url) if post.audio_url else ""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{post.title}</title>
    {css_style}
</head>
<body>
    <article>
        <header>
            <h1>{post.title}</h1>
            <div class="post-meta">
                {date_html}
                <div class="post-description">{post.description}</div>
                {audio_html}
            </div>
        </header>
        <div class="post-content">{post.body_html}</div>
    </article>
    <footer>
        <p>Archived from Substack</p>
    </footer>
</body>
</html>"""

    def save_html_file(self, title: str, html_content: str) -> str | None:
        file_name = serialize(title)
        file_path = self.html_path / f"{file_name}.html"

        if not file_path.is_file():
            logger.debug(f"Attempting to save HTML file: {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.existing_html_files.add(file_path.name)
            logger.debug(f"Successfully saved HTML file: {file_path}")
            return str(file_path)
        else:
            logger.debug(f"HTML file already exists, skipping: {file_path}")
            return None

    async def convert_single_html_to_text(self, html_file_path: str) -> None:
        loop = asyncio.get_running_loop()
        html_file_path_obj = Path(html_file_path)
        relative_path = html_file_path_obj.relative_to(self.html_path)
        text_file_path = self.text_path / relative_path.with_suffix(".txt")

        text_file_path.parent.mkdir(parents=True, exist_ok=True)

        def _sync_convert() -> str:
            with open(html_file_path_obj, "r", encoding="utf-8") as f:
                html_content = f.read()
            return cast(str, html2text.html2text(self._clean_html_for_text_conversion(html_content)))

        text_content = cast(str, await loop.run_in_executor(None, _sync_convert))

        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(text_content)

    def _get_css_style(self) -> str:
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

    def _format_date_html(self, date: str) -> str:
        if not date:
            return ""

        try:
            date_obj = datetime.fromisoformat(date.replace("Z", "+00:00"))
            formatted_date = date_obj.strftime("%B %d, %Y")
            return f'<div class="post-date">{formatted_date}</div>'
        except ValueError as e:
            logger.warning(f"Error parsing date format: {e}")
            return f'<div class="post-date">{date}</div>'

    def _format_audio_html(self, audio: str) -> str:
        return f'<p>Audio link: <a href="{audio}">Listen to audio</a></p>' if audio else ""

    def _clean_html_for_text_conversion(self, html_content: str) -> str:
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove social sharing buttons and related elements
        for element in soup.find_all(
            "div",
            class_=[
                "modal",
                "post-ufi",
                "pencraft pc-display-flex pc-flexDirection-column pc-gap-24 pc-padding-24 pc-reset bg-primary-zk6FDl border-detail-EGrm7T pc-borderRadius-md container-xiJVit",
            ],
        ):
            if isinstance(element, Tag):
                element.decompose()

        # Remove subscription prompts
        for element in soup.find_all(
            "div", class_="pencraft pc-display-flex pc-flexDirection-column pc-gap-20 pc-reset"
        ):
            if isinstance(element, Tag):
                element.decompose()
        for element in soup.find_all("div", class_="subscribe-widget"):
            if isinstance(element, Tag):
                element.decompose()
        for element in soup.find_all("ul", class_="dropdown-menu tooltip subscribe-prompt-dropdown free"):
            if isinstance(element, Tag):
                element.decompose()

        # Remove image containers (if they add noise)
        for element in soup.find_all("div", class_="captioned-image-container"):
            if isinstance(element, Tag):
                element.decompose()

        # Remove empty header anchors
        for element in soup.find_all(class_="header-anchor-post"):
            if not element.get_text(strip=True):
                if isinstance(element, Tag):
                    element.decompose()

        # Remove empty divs and dividers
        for element in soup.find_all("div", class_="visibility-check"):
            if isinstance(element, Tag):
                element.decompose()
        for element in soup.find_all("div", class_="divider-Ti4OTa"):
            if isinstance(element, Tag):
                element.decompose()

        # Remove footer
        footer = soup.find("footer")
        if footer:
            if isinstance(footer, Tag):
                footer.decompose()

        # Remove any remaining script and style tags
        for element in soup(["script", "style"]):
            if isinstance(element, Tag):
                element.decompose()

        return str(soup)
