from loguru import logger
from playwright.async_api import Browser
from rich.progress import Progress

from app.models import Post
from app.repositories.file_repository import FileRepository
from app.repositories.substack_repository import SubstackRepository


class ArchiverService:
    def __init__(
        self,
        substack_handle: str,
        base_url: str,
        browser: Browser,
        progress: Progress,
        output_directory: str = "./archive",
        skip_existing: bool = True,
    ) -> None:
        self.substack_handle = substack_handle
        self.base_url = base_url
        self.browser = browser
        self.substack_repository = SubstackRepository(base_url, browser)
        self.file_repository = FileRepository(substack_handle, output_directory)
        self.progress = progress
        self.task_id = self.progress.add_task(f"[cyan]{self.substack_handle}[/cyan]", total=None)
        self.skip_existing = skip_existing

    async def archive(self) -> None:
        page = await self.substack_repository.get_page()
        all_posts_data = await self.substack_repository.get_posts(page, self.progress, self.task_id)
        self.file_repository.dump_to_json(all_posts_data)

        body_none_count = 0
        downloaded_posts_count = 0

        for post_data_dict in all_posts_data:
            post = Post.from_dict(post_data_dict)

            if post.title and self.skip_existing and self.file_repository.html_file_exists(post.title):
                logger.debug(f"Skipping existing post: {post.title}")
                continue

            if post.title and post.body_html:
                html_content = self.file_repository.create_html_template(post)
                saved_file_path = self.file_repository.save_html_file(post.title, html_content)
                if saved_file_path:
                    await self.file_repository.convert_single_html_to_text(saved_file_path)
                    downloaded_posts_count += 1

            else:
                body_none_count += 1
                logger.debug(f"Skipping post '{post.title}' due to missing body_html or title.")

        self.progress.update(self.task_id, description=f"[green]{self.substack_handle} (Done)[/green]")
        self.progress.remove_task(self.task_id)

        logger.debug(f"Number of downloaded posts: {downloaded_posts_count}")
        logger.debug(f"Number of posts without body: {body_none_count}")

        if body_none_count > 0:
            logger.debug("Some posts might be inaccessible. Check if you have the necessary permissions.")

        logger.debug("Done for this substack!")
