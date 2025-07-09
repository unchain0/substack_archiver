import re
from datetime import datetime
from loguru import logger
from bs4 import BeautifulSoup, Tag


def serialize(value: str) -> str:
    if not isinstance(value, str):
        logger.error(f"Error serializing: {value} is not a string")

    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"[-\s]+", "-", value).strip("-")


def get_css_style() -> str:
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


def format_date_html(date: str) -> str:
    if not date:
        return ""

    try:
        date_obj = datetime.fromisoformat(date.replace("Z", "+00:00"))
        formatted_date = date_obj.strftime("%B %d, %Y")
        return f'<div class="post-date">{formatted_date}</div>'
    except ValueError as e:
        logger.warning(f"Error parsing date format: {e}")
        return f'<div class="post-date">{date}</div>'


def format_audio_html(audio: str) -> str:
    return f'<p>Audio link: <a href="{audio}">Listen to audio</a></p>' if audio else ""


def clean_html_for_text_conversion(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove social sharing buttons and related elements
    for element in soup.find_all("div", class_=["modal", "post-ufi", "pencraft pc-display-flex pc-flexDirection-column pc-gap-24 pc-padding-24 pc-reset bg-primary-zk6FDl border-detail-EGrm7T pc-borderRadius-md container-xiJVit"]):
        if isinstance(element, Tag):
            element.decompose()

    # Remove subscription prompts
    for element in soup.find_all("div", class_="pencraft pc-display-flex pc-flexDirection-column pc-gap-20 pc-reset"):
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
