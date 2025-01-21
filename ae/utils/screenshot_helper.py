import aiofiles, time, base64, tempfile
from ae.utils.logger import logger

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

async def screenshot_page(page):
    new_screenshot = await page.screenshot()
    current_timestamp = "_" + int(time.time()).__str__()
    screenshot_png_name = tempfile.mktemp(prefix='page-screenshot-', suffix=f"{current_timestamp}.png")
    async with aiofiles.open(screenshot_png_name, "wb") as file:  # type: ignore
        await file.write(new_screenshot)  # type: ignore
    logger.info(f"Screenshot saved as {screenshot_png_name}")
    return {"type": "image_url", "image_url": "data:image/png;base64," + encode_image(screenshot_png_name)}
