import asyncio
from playwright.async_api import async_playwright
import json
import re
import os
from dotenv import load_dotenv
import sys
from colors import log, welcome_message

load_dotenv("config.env")

def command_line_parser():
    if len(sys.argv) != 3:
        log("""Usage: python3 substack_archiver.py "SUBSSTACKNAME" "URL", """, "white")
        log("""Example: python3 substack_archiver.py "abc" "https://abc.substack.com/" or with custom domain: "name123" "https://abc.com/" """, "white")
        print("")
        sys.exit(1)
    else:
        return sys.argv[1], sys.argv[2]

class SubstackPlaywrightHandler:
    def __init__(self, substack_handle, base_url):
        self.substack_handle = substack_handle
        self.base_url = base_url
        self.post_url = f"{self.base_url}api/v1/posts?limit=50&offset="
        self.html_path = f"html_dumps/{substack_handle}"
        self.json_path = f"json_dumps/{substack_handle}"
        
        os.makedirs(self.html_path, exist_ok=True)
        os.makedirs(self.json_path, exist_ok=True)

    async def get_posts(self, page):
        post_requests = []
        for i in range(0, 500, 50):
            post_url = f"{self.post_url}{i}"
            await page.goto(post_url)
            content = await page.content()
            try:
                posts = json.loads(await page.evaluate('() => document.body.innerText'))
                if not posts:
                    break
                post_requests.append(posts)
            except json.JSONDecodeError:
                log(f"Error parsing JSON at offset {i}", "red")
                break
            await asyncio.sleep(2)  # Sleep to avoid rate limiting
        return post_requests

    def dump_to_json(self, post_requests):
        for i, posts in enumerate(post_requests):
            with open(f"{self.json_path}/dump{i}.json", "w") as f:
                json.dump(posts, f)

    @staticmethod
    def serialize(value): 
        value = str(value)
        value = re.sub(r"[^\w\s-]", "", value)
        return re.sub(r"[-\s]+", "-", value).strip('-')

    def parse_to_html(self, post_requests):
        log("Parsing posts to HTML...", "white")

        all_titles = []
        all_bodies = []
        all_descriptions = []
        body_none = []
        audio_files = []

        for posts in post_requests:
            for post in posts:
                all_titles.append(post["title"])
                all_descriptions.append(post["description"])
                audio_files.append(post.get("podcast_url", ""))
                if post["body_html"] is None:
                    body_none.append(post["title"])
                else:   
                    all_bodies.append(post["body_html"])

        for title, body, description, audio in zip(all_titles, all_bodies, all_descriptions, audio_files):
            audio_html = f'<p>Audio link: <a href="{audio}">Listen to audio</a></p>' if audio else ""
            if body is None:
                continue
            html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body>
    <h1>{title}</h1>
    <p>{description}</p>
    {audio_html}
    <div>{body}</div>
</body>
</html>"""
            file_name = self.serialize(title)
            
            if not os.path.isfile(f"{self.html_path}/{file_name}.html"):
                with open(f"{self.html_path}/{file_name}.html", "w", encoding="utf-8") as f:
                    f.write(html_template)

        return body_none, all_titles, audio_files

async def main():
    welcome_message()

    substack_handle, base_url = command_line_parser()
    handler = SubstackPlaywrightHandler(substack_handle, base_url)
    log(f"Started scraping process, please wait...", "red")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # Set headless to False
        page = await browser.new_page()

        post_requests = await handler.get_posts(page)
        handler.dump_to_json(post_requests)
        html_result = handler.parse_to_html(post_requests)

        await browser.close()

    log(f"Number of downloaded posts: {len(html_result[1])}", "green")
    log(f"Number of posts without body: {len(html_result[0])}", "red")

    if html_result[0]:
        log(f"Number of Inaccessible Posts: {len(html_result[0])}", "red")
        log("Some posts might be inaccessible. Check if you have the necessary permissions.", "yellow")

    print("")
    log("Done!", "green", "bold")
    print("")

if __name__ == "__main__":
    asyncio.run(main())
