import asyncio
import json
import os
import time
import argparse
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import re

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
    links = await page.evaluate('''
        () => {
            const links = [];
            document.querySelectorAll('a').forEach(link => {
                links.push(link.href);
            });
            return links;
        }
    ''')
    pattern = re.compile(r'https://leakedzone\.com/[^/]+/(photo|video)/\d+')
    filtered_links = [link for link in links if pattern.match(link)]
    return filtered_links

async def run_helper_script(script_name, link, folder, debug_headless):
    """Runs the specified helper script (photohelper.py or videohelper.py) without concurrency control."""
    command = ['python', script_name, link, folder]
    if debug_headless:
        command.append('--debug-headless')

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        print(f"{script_name} completed successfully for {link}.")
    else:
        print(f"Error in {script_name} for {link}: {stderr.decode()}")

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

        # Process each link one at a time
        for link in links:
            # Extract username from the URL
            username = link.split('/')[3]  # Adjust as needed based on URL structure

            if 'photo' in link:
                photo_folder = os.path.join(os.getcwd(), username, 'photos')
                await run_helper_script('photohelper.py', link, photo_folder, debug_headless)
            elif 'video' in link:
                video_folder = os.path.join(os.getcwd(), username, 'videos')
                await run_helper_script('videohelper.py', link, video_folder, debug_headless)

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
