from .config import IS_LINUX

LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]


async def create_browser(playwright):
    args = LAUNCH_ARGS.copy()
    if not IS_LINUX:
        args += ["--window-position=-32000,-32000", "--window-size=1,1"]

    browser = await playwright.chromium.launch(
        channel="chrome",
        headless=False,
        args=args,
    )
    context = await browser.new_context(
        viewport={"width": 1280, "height": 720},
        locale="pt-BR",
    )
    return browser, context
