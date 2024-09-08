# lz-scrape.py
import asyncio
import json
import os
import time
import argparse
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import re
import aiohttp
from PIL import Image
from io import BytesIO
import subprocess  # For calling videohelper.py

# Load environment variables from config.env
load_dotenv('config.env')
config = json.loads(os.getenv('USER_CONFIG'))

# Argument Parsing
parser = argparse.ArgumentParser(description="Script to scrape a webpage with infinite scroll.")
parser.add_argument("url", help="The URL of the page to scrape.")
parser.add_argument("-dh", "--debug-headless", action="store_true", help="Enable debug mode with visible browser.")
args = parser.parse_args()

url = args.url
debug_headless = args.debug_headless

# Read user agent and cookies from config
user_agent = config.get('userAgent', 'Mozilla/5.0')
cookies = config.get('leakedzone.com', {})

async def scroll_to_bottom(page):
    previous_height = await page.evaluate('document.body.scrollHeight')
    while True:
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(2000)  # Wait for new content to load
        current_height = await page.evaluate('document.body.scrollHeight')
        if current_height == previous_height:
            break
        previous_height = current_height
    print('Reached the bottom of the page.')

async def extract_links(page):
    # Extract links from the page
    links = await page.evaluate('''
        () => {
            const links = [];
            document.querySelectorAll('a').forEach(link => {
                links.push(link.href);
            });
            return links;
        }
    ''')
    # Filter links using the provided pattern
    pattern = re.compile(r'https://leakedzone\.com/[^/]+/(photo|video)/\d+')
    filtered_links = [link for link in links if pattern.match(link)]
    return filtered_links

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

async def download_images(image_urls, username_folder, dh=False):
    photos_folder = os.path.join(username_folder, 'photos')
    os.makedirs(photos_folder, exist_ok=True)
    
    async with aiohttp.ClientSession() as session:
        for photo_url in image_urls:
            filename = os.path.basename(photo_url)
            file_path = os.path.join(photos_folder, filename)
            if not os.path.exists(file_path):
                try:
                    async with session.get(photo_url) as response:
                        if response.status == 200:
                            content = await response.read()
                            # Validate image content
                            try:
                                Image.open(BytesIO(content)).verify()
                                with open(file_path, 'wb') as f:
                                    f.write(content)
                                if dh:
                                    print(f"Downloaded {filename} to {photos_folder}")
                            except (IOError, SyntaxError) as e:
                                print(f"Image validation failed for {filename}: {e}")
                        elif response.status == 404:
                            print(f"Image not found: {photo_url}")
                        else:
                            print(f"Failed to download {filename}, status code {response.status}")
                except Exception as e:
                    print(f"Exception occurred while downloading {filename}: {e}")
            else:
                if dh:
                    print(f"Skipping {filename} as it already exists")

async def download_photos(page, link, dh=False):
    # Extract username from URL
    username_regex = re.compile(r'https://leakedzone\.com/([^/]+)/')
    username_match = username_regex.search(link)
    if username_match:
        username = username_match.group(1)  # Extract the first capturing group
    else:
        raise ValueError("Invalid URL format")

    # Create username folder and photos subfolder
    username_folder = os.path.join(os.getcwd(), username)
    
    # Extract image URLs from the detail page
    await page.goto(link)
    image_urls = await extract_image_urls(page)
    await download_images(image_urls, username_folder, dh)

async def download_videos(link, dh=False):
    # Extract username from URL
    username_regex = re.compile(r'https://leakedzone\.com/([^/]+)/')
    username_match = username_regex.search(link)
    if username_match:
        username = username_match.group(1)  # Extract the first capturing group
    else:
        raise ValueError("Invalid URL format")

    # Create username folder and videos subfolder
    username_folder = os.path.join(os.getcwd(), username)
    videos_folder = os.path.join(username_folder, 'videos')
    os.makedirs(videos_folder, exist_ok=True)
    
    # Call your existing videohelper.py and pass the video link and username folder
    subprocess.run(['python', 'videohelper.py', link, videos_folder])

async def main():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=not debug_headless)  # Use Firefox
        context = await browser.new_context(user_agent=user_agent)

        # Set cookies
        for domain, cookies_dict in cookies.items():
            for cookie_name, cookie_data in cookies_dict.items():
                await context.add_cookies([cookie_data])

        page = await context.new_page()
        print(f'Navigating to: {url}')
        await page.goto(url, wait_until='domcontentloaded')

        await scroll_to_bottom(page)

        links = await extract_links(page)

        # Download photos or delegate videos to videohelper.py
        for link in links:
            if 'photo' in link:
                await download_photos(page, link, debug_headless)
            elif 'video' in link:
                await download_videos(link, debug_headless)

        # Dump links to a text file
        with open('links.txt', 'w') as f:
            for link in links:
                f.write(link + '\n')

        if debug_headless:
            print("Debug mode active, keeping browser open...")
            time.sleep(10)  # Keep browser open for a while to debug

        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
