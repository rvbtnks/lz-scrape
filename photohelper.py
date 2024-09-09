import asyncio
import json
import os
import argparse
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import aiohttp

# Load environment variables from config.env
load_dotenv('config.env')
config = json.loads(os.getenv('USER_CONFIG'))

# Argument Parsing
parser = argparse.ArgumentParser(description="Script to scrape image URLs and download images.")
parser.add_argument("url", help="The URL of the page to scrape.")
parser.add_argument("username_folder", help="The folder to save downloaded images, named after the user.")
parser.add_argument("-dh", "--debug-headless", action="store_true", help="Enable debug mode with visible browser.")
args = parser.parse_args()

url = args.url
username_folder = args.username_folder
debug_headless = args.debug_headless

# Read user agent and cookies from config
user_agent = config.get('userAgent', 'Mozilla/5.0')
cookies = config.get('leakedzone.com', {})

# Ensure the images folder exists
images_folder = os.path.join(username_folder)
os.makedirs(images_folder, exist_ok=True)

async def extract_image_urls(page):
    # Extract image URLs from the detail page
    image_urls = await page.evaluate('''
        () => {
            const urls = [];
            document.querySelectorAll('img[src*="storage/images/"]').forEach(img => {
                urls.push(img.src);
            });
            return urls;
        }
    ''')
    return image_urls

async def download_image(url, folder):
    # Ensure the download folder exists
    os.makedirs(folder, exist_ok=True)
    
    filename = os.path.basename(url)
    file_path = os.path.join(folder, filename)
    
    # Check if the file already exists
    if os.path.exists(file_path):
        print(f"Image {filename} already exists. Skipping download.")
        return  # Skip the download if the file already exists

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    print(f"Downloaded {filename} to {folder}")
                else:
                    print(f"Failed to download image {url}, status code {response.status}")
        except Exception as e:
            print(f"Exception occurred while downloading {url}: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=not debug_headless)
        context = await browser.new_context(user_agent=user_agent)

        # Set cookies
        for domain, cookies_dict in cookies.items():
            for cookie_name, cookie_data in cookies_dict.items():
                await context.add_cookies([cookie_data])

        page = await context.new_page()
        print(f'Navigating to: {url}')
        await page.goto(url, wait_until='domcontentloaded')

        # Wait for the page to fully load
        await page.wait_for_load_state('networkidle')

        image_urls = await extract_image_urls(page)
        print(f"Found {len(image_urls)} image(s)")

        # Download images
        if image_urls:
            for image_url in image_urls:
                await download_image(image_url, images_folder)

        if debug_headless:
            print("Debug mode active, keeping browser open...")
            await asyncio.sleep(10)  # Keep browser open for a while to debug

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
