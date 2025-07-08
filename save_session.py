import asyncio
from playwright.async_api import async_playwright


async def save_session_state():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Set to False to see the browser
        context = await browser.new_context()
        page = await context.new_page()

        print("Please log in to Substack in the opened browser window.")
        print("Once logged in, close the browser window.")
        print("Then, press Enter in this terminal to save the session.")

        await page.goto("https://yohannbtc.substack.com/account/login")

        # Wait for user to press Enter in the terminal
        input("Press Enter to continue...")

        # Save the storage state
        await context.storage_state(path="storage_state.json")
        print("Session state saved to storage_state.json")

        await browser.close()  # Explicitly close the browser


if __name__ == "__main__":
    asyncio.run(save_session_state())
