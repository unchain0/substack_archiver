import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


async def save_session_state():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        print("Please log in to Substack in the opened browser window.")
        print("Once logged in, close the browser window.")
        print("Then, press Enter in this terminal to save the session.")

        await page.goto("https://substack.com/sign-in")

        input("Press Enter to continue...")

        # Save the storage state
        storage_state_path = Path("storage_state.json")
        await context.storage_state(path=str(storage_state_path))
        print(f"Session state saved to {storage_state_path}")

        await browser.close()  # Explicitly close the browser


if __name__ == "__main__":
    asyncio.run(save_session_state())
