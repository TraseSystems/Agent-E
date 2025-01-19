import os
import time
from typing import Annotated
from typing import Any
import tempfile
import json

from playwright.async_api import Page

from ae.config import SOURCE_LOG_FOLDER_PATH
from ae.core.playwright_manager import PlaywrightManager
from ae.utils.dom_helper import wait_for_non_loading_dom_state
from ae.utils.get_detailed_accessibility_tree import do_get_accessibility_info
from ae.utils.logger import logger
from ae.utils.ui_messagetype import MessageType


def truncate_fields(fields: dict[str, Any], url: str = "") -> dict[str, Any] | str:
    # this should only happen in extreme cases
    if len(str(fields)) > 40_000:
        outfile = tempfile.mktemp(prefix='page-dom-content-', suffix=".json")
        with open(outfile, 'w+', encoding='utf-8') as f:
            json.dump(fields, f, indent=2)

        logger.warning(f"DOM content was too large to display for {url}, saved to {outfile}")

        msg = f"""The page DOM was too large to display, so it was saved to this JSON file: {outfile}

A preview of the DOM content is shown below:

{json.dumps(fields, indent=2)[:1000]}...
        
To analyze the full text content, use your `python_interpreter` tool to read the file contents using:

```
import json
with open('{outfile}', 'r') as f:
    dom_content = json.load(f)
```
"""
        logger.warning(msg)
        return msg
    else:
        return fields


async def get_dom_with_content_type(
    content_type: Annotated[str, "The type of content to extract: 'text_only': Extracts the innerText of the highest element in the document and responds with text, or 'input_fields': Extracts the text input and button elements in the dom."]
    ) -> Annotated[dict[str, Any] | str | None, "The output based on the specified content type."]:
    """
    Retrieves and processes the DOM of the active page in a browser instance based on the specified content type.

    Parameters
    ----------
    content_type : str
        The type of content to extract. Possible values are:
        - 'text_only': Extracts the innerText of the highest element in the document and responds with text.
        - 'input_fields': Extracts the text input and button elements in the DOM and responds with a JSON object.
        - 'all_fields': Extracts all the fields in the DOM and responds with a JSON object.

    Returns
    -------
    dict[str, Any] | str | None
        The processed content based on the specified content type. This could be:
        - A JSON object for 'input_fields' with just inputs.
        - Plain text for 'text_only'.
        - A minified DOM represented as a JSON object for 'all_fields'.

    Raises
    ------
    ValueError
        If an unsupported content_type is provided.
    """

    logger.info(f"Executing Get DOM Command based on content_type: {content_type}")
    start_time = time.time()
    # Create and use the PlaywrightManager
    browser_manager = PlaywrightManager(browser_type='chromium', headless=False)
    page = await browser_manager.get_current_page()
    if page is None: # type: ignore
        raise ValueError('No active page found. OpenURL command opens a new page.')

    extracted_data = None
    await wait_for_non_loading_dom_state(page, 2000) # wait for the DOM to be ready, non loading means external resources do not need to be loaded
    user_success_message = ""
    if content_type == 'all_fields':
        user_success_message = "Fetched all the fields in the DOM"
        extracted_data = await do_get_accessibility_info(page, only_input_fields=False)
        extracted_data = truncate_fields(extracted_data)
    elif content_type == 'input_fields':
        logger.debug('Fetching DOM for input_fields')
        extracted_data = await do_get_accessibility_info(page, only_input_fields=True)
        if extracted_data is None:
            return "Could not fetch input fields. Please consider trying with content_type all_fields."
        extracted_data = truncate_fields(extracted_data)
        user_success_message = "Fetched only input fields in the DOM"
    elif content_type == 'text_only':
        # Extract text from the body or the highest-level element
        logger.debug('Fetching DOM for text_only')
        text_content = await get_filtered_text_content(page)
        with open(os.path.join(SOURCE_LOG_FOLDER_PATH, 'text_only_dom.txt'), 'w',  encoding='utf-8') as f:
            f.write(text_content)
        extracted_data = str(text_content)

        if len(extracted_data) > 20_000: # 20k ~= 7000 tokens
            # save to a text file
            outfile = tempfile.mktemp(prefix='page-text-content-', suffix=".txt")
            with open(outfile, 'w+', encoding='utf-8') as f:
                f.write(extracted_data)
            extracted_data = f"""The page text was too large to display, so it was saved to this text file: {outfile}

A preview of the text content is shown below:

{extracted_data[:1000]}...

To analyze the full text content, use your `python_interpreter` tool to read the file contents."""

        video_urls = await get_video_urls(page)
        pdf_urls = await get_pdf_urls(page)
        extracted_data += f"\n\nThis is the list of video URLs on the page in the order they appear: {str(video_urls)}"
        extracted_data += f"\n\nThis is the list of PDF URLs on the page in the order they appear: {str(pdf_urls)}"

        user_success_message = "Fetched the text content of the DOM"
    # elif content_type == "video_urls":
    #     logger.debug('Fetching DOM for video_urls')
    #     video_urls = await get_video_urls(page)
    #     extracted_data = f"This is the list of video URLs on the page in the order they appear: {str(video_urls)}"
    # elif content_type == "pdf_urls":
    #     logger.debug('Fetching DOM for pdf_urls')
    #     pdf_urls = await get_pdf_urls(page)
    #     extracted_data = f"This is the list of PDF URLs on the page in the order they appear: {str(pdf_urls)}"
    else:
        raise ValueError(f"Unsupported content_type: {content_type}")

    elapsed_time = time.time() - start_time
    logger.info(f"Get DOM Command executed in {elapsed_time} seconds")
    await browser_manager.notify_user(user_success_message, message_type=MessageType.ACTION)
    return extracted_data # type: ignore


async def get_filtered_text_content(page: Page) -> str:
    text_content = await page.evaluate("""
        () => {
            // Array of query selectors to filter out
            const selectorsToFilter = ['#agente-overlay'];

            // Store the original visibility values to revert later
            const originalStyles = [];

            // Hide the elements matching the query selectors
            selectorsToFilter.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(element => {
                    originalStyles.push({ element: element, originalStyle: element.style.visibility });
                    element.style.visibility = 'hidden';
                });
            });

            // Get the text content of the page
            let textContent = document?.body?.innerText || document?.documentElement?.innerText || "";

            // Get all the alt text from images on the page
            let altTexts = Array.from(document.querySelectorAll('img')).map(img => img.alt);
            altTexts="Other Alt Texts in the page: " + altTexts.join(' ');

            // Revert the visibility changes
            originalStyles.forEach(entry => {
                entry.element.style.visibility = entry.originalStyle;
            });
            textContent=textContent+" "+altTexts;
            return textContent;
        }
    """)
    return text_content


def ordered_unique_urls(urls: list):
    if not isinstance(urls, list):
        logger.warning(f"Expected a list of URLs, but got {type(urls)}")
        return []

    # Filter out empty entries
    urls = [url for url in urls if url]

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for url in urls:
        if url not in seen:
            unique_urls.append(url)
            seen.add(url)
    return unique_urls


async def get_video_urls(page: Page) -> list[str]:
    urls = await page.evaluate("""
    () => {
        return Array.from(
            document.querySelectorAll(
                // Grab elements that have src containing .gif, .mp4, .mov
                'img[src*=".gif"], img[src*=".GIF"], ' +
                'video[src*=".mp4"], video[src*=".MP4"], video[src*=".mov"], video[src*=".MOV"], ' +
                'source[src*=".mp4"], source[src*=".MP4"], source[src*=".mov"], source[src*=".MOV"]'
            ),
            el => el.src
        );
    }
    """)
    return ordered_unique_urls(urls)


async def get_pdf_urls(page: Page) -> list[str]:
    urls = await page.evaluate("""
    () => {
      return Array.from(
        document.querySelectorAll('a[href*=".pdf"], a[href*=".PDF"], img[src*=".pdf"], img[src*=".PDF"]'),
        el => {
          if (el.tagName.toLowerCase() === 'a') {
            return el.href;
          } else if (el.tagName.toLowerCase() === 'img') {
            return el.src;
          }
          return '';
        }
      );
    }
    """)
    return ordered_unique_urls(urls)