import inspect
from typing import Annotated

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import ConsoleMessage

from ae.core.playwright_manager import PlaywrightManager
from ae.utils.logger import logger
from ae.utils.ui_messagetype import MessageType
from ae.utils.screenshot_helper import screenshot_page

class SolveState:
    """
    A simple class to track the state of the CAPTCHA solution.
    """

    started = False
    finished = False

    # These messages are sent to the browser's console automatically
    # when a CAPTCHA is detected and solved.
    START_MSG = "browserbase-solving-started"
    END_MSG = "browserbase-solving-finished"

    def handle_console(self, msg: ConsoleMessage) -> None:
        """
        Handle messages coming from the browser's console.
        """
        if msg.text == self.START_MSG:
            self.started = True
            logger.info("AI has started solving the CAPTCHA...")
            return

        if msg.text == self.END_MSG:
            self.finished = True
            logger.info("AI solved the CAPTCHA!")
            return

async def attempt_goto(page, url, timeout):
    # BrowserBase rec: 60 seconds is a good timeout for most pages (for no CAPTCHA, you need to wait this long to proceed)
    await page.goto(url, timeout=timeout*1000) # type: ignore
    logger.info("page.goto finished, waiting for CAPTCHA messages. url=%s", url)

    async with page.expect_console_message(
        lambda msg: msg.text == SolveState.END_MSG,
        timeout=30_000,
    ):
        # Wait until the END_MSG console message is observed or times out.
        pass


async def openurl(url: Annotated[str, "The URL to navigate to. Value must include the protocol (http:// or https://)."],
            timeout: Annotated[int, "Additional wait time in seconds after initial load."] = 60) -> Annotated[str, "Returns the result of this request in text form"]:
    """
    Opens a specified URL in the active browser instance. Waits for an initial load event, then waits for either
    the 'domcontentloaded' event or a configurable timeout, whichever comes first.

    Parameters:
    - url: The URL to navigate to.
    - timeout: Additional time in seconds to wait after the initial load before considering the navigation successful.

    Returns:
    - URL of the new page.
    """
    logger.info(f"Opening URL: {url}")
    # check if URL is a PDF
    if url.endswith('.pdf'):
        return f"This tool should not be used with PDFs, call the `get_webpage_info` tool instead"
    browser_manager = PlaywrightManager(browser_type='chromium', headless=False)
    await browser_manager.get_browser_context()
    page = await browser_manager.get_current_page()
    
    state = SolveState()
    page.on("console", state.handle_console)
    
    try:
        url = ensure_protocol(url)
        if page.url == url:
            logger.info(f"Current page URL is the same as the new URL: {url}. No need to refresh.")
            title = await page.title()
            return f"Page already loaded: {url}, Title: {title}" # type: ignore

        # Navigate to the URL with a short timeout to ensure the initial load starts
        function_name = inspect.currentframe().f_code.co_name # type: ignore
        
        await browser_manager.take_screenshots(f"{function_name}_start", page)

        await attempt_goto(page, url, timeout)

    except PlaywrightTimeoutError as pte:
        logger.warning(f"Initial navigation to {url} failed: {pte}. Will try to continue anyway.") # happens more often than not, but does not seem to be a problem
        if state.started:
            logger.error(f"CAPTCHA started solving but didn't finish: started={state.started} finished={state.finished}, url={url}")
    except Exception as e:
        logger.error(f"An error occurred while opening the URL: {url}. Error: {e}")

        if 'Target page, context or browser has been closed' in str(e):
            logger.error(f"Something was closed while opening the URL, so retrying a second time. url={url}, error={e}")
            state.started = False
            state.finished = False
            try:
                await attempt_goto(page, url, timeout)
                logger.info(f"Successfully opened the URL a second time. url={url}")
            except:
                logger.error(f"An error occurred while opening the URL a second time. url={url}, error={e}")
                traceback.print_exc()

    # If we didn't see both a start and finish message, raise an error.
    if state.started == state.finished == False:
        logger.warning("No CAPTCHA was presented, or was solved too quick to see. url=%s", url)
    else:
        logger.info("CAPTCHA is complete, url=%s", url)

    logger.info("Waiting for body to load, url=%s", url)
    await page.locator("body").wait_for(state="visible")

    await browser_manager.take_screenshots(f"{function_name}_end", page)

    await browser_manager.notify_user(f"Opened URL: {url}", message_type=MessageType.ACTION)

    # Get the page title
    title = await page.title()
    url = page.url

    text = f"Page loaded: {url}, Title: '{title}'"
    screenshot_msg = await screenshot_page(page)
    return [
        {"type": "text", "text": text},
        screenshot_msg,
    ]
    

def ensure_protocol(url: str) -> str:
    """
    Ensures that a URL has a protocol (http:// or https://). If it doesn't have one,
    https:// is added by default.

    Parameters:
    - url: The URL to check and modify if necessary.

    Returns:
    - A URL string with a protocol.
    """
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url  # Default to http if no protocol is specified
        logger.info(f"Added 'https://' protocol to URL because it was missing. New URL is: {url}")
    return url
