from typing import Any

from loguru import logger
from playwright.async_api import Browser

from app.models import Post
from app.repositories.file_repository import FileRepository
from app.repositories.substack_repository import SubstackRepository


class ArchiverService:
    def __init__(self, substack_handle: str, base_url: str, browser: Browser) -> None:
        self.substack_handle = substack_handle
        self.base_url = base_url
        self.browser = browser
        self.substack_repository = SubstackRepository(base_url, browser)
        self.file_repository = FileRepository(substack_handle)

    async def archive(self) -> None:
        page = await self.substack_repository.get_page()
        posts = await self.substack_repository.get_posts(page)
        self.file_repository.dump_to_json(posts)

        body_none_count = 0
        downloaded_posts_count = 0

        for post_data_dict in posts:
            post = Post.from_dict(post_data_dict)

            if post.title and post.body_html:
                html_content = self.file_repository.create_html_template(post)
                saved_file_path = self.file_repository.save_html_file(post.title, html_content)
                if saved_file_path:
                    await self.file_repository.convert_single_html_to_text(saved_file_path)
                    downloaded_posts_count += 1
            else:
                body_none_count += 1
                logger.warning(f"Skipping post '{post.title}' due to missing body_html or title.")


        logger.success(f"Number of downloaded posts: {downloaded_posts_count}")
        logger.error(f"Number of posts without body: {body_none_count}")

        if body_none_count > 0:
            logger.warning("Some posts might be inaccessible. Check if you have the necessary permissions.")

        logger.success("Done for this substack!")
