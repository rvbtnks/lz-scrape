import asyncio
import json
import os
import argparse
import subprocess
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# Load environment variables from config.env
load_dotenv('config.env')
config = json.loads(os.getenv('USER_CONFIG'))

# Argument Parsing
parser = argparse.ArgumentParser(description="Script to monitor network requests.")
parser.add_argument("url", help="The URL of the page to monitor.")
parser.add_argument("username_folder", help="The folder to save videos, named after the user.")
parser.add_argument("-dh", "--debug-headless", action="store_true", help="Enable debug mode with visible browser.")
args = parser.parse_args()

url = args.url
debug_headless = args.debug_headless
username_folder = args.username_folder

# Read user agent and cookies from config
user_agent = config.get('userAgent', 'Mozilla/5.0')
cookies = config.get('leakedzone.com', {})

# Ensure the videos folder exists
videos_folder = username_folder
os.makedirs(videos_folder, exist_ok=True)

async def handle_request(request):
    if ".m3u8" in request.url:
        print(f"Found .m3u8 file: {request.url}")
        await download_video(request.url)

async def download_video(m3u8_url):
    base_filename = os.path.join(videos_folder, "video")
    extension = ".mp4"
    filename = f"{base_filename}0001{extension}"
    
    # Check if the file exists and increment the filename if needed
    counter = 1
    while os.path.exists(filename):
        counter += 1
        filename = f"{base_filename}{counter:04d}{extension}"
    
    print(f"Downloading video to {filename}")
    command = [
        "yt-dlp",
        "-o", filename,
        m3u8_url
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Download completed: {filename}")
    else:
        print(f"Error downloading video: {result.stderr}")

async def click_center(page):
    # Wait until the page is fully loaded
    await page.wait_for_load_state('networkidle')
    
    # Ensure viewport size is available
    viewport = page.viewport_size
    if viewport:
        center_x = viewport['width'] // 2
        center_y = viewport['height'] // 2
        await page.mouse.click(center_x, center_y)
        print(f"Clicked at the center of the page: ({center_x}, {center_y})")
    else:
        print("Viewport size is not available.")

async def main():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=not debug_headless)
        context = await browser.new_context(user_agent=user_agent)
        
        # Set cookies in Playwright
        for domain, cookies_dict in cookies.items():
            for cookie_name, cookie_data in cookies_dict.items():
                await context.add_cookies([cookie_data])

        page = await context.new_page()
        
        # Monitor network requests
        page.on('request', handle_request)

        print(f'Navigating to: {url}')
        await page.goto(url, wait_until='domcontentloaded')

        # Click in the center of the page
        await click_center(page)
        
        # Keep browser open for debugging
        if debug_headless:
            print("Debug mode active, keeping browser open...")
            await asyncio.sleep(10)

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
