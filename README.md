# lz-scrape
leakedzone scraper in python

requires yt-dlp and geckodriver

usage: python lz-scrape.py http://url

it will create a folder based on the model, photos will go into photos, videos will go into videos.

cookie needs to be put into the config.env file

easiest way to grab the cookie is:
FlagCookies Extension

Click on the Preferences -->  "Export cookie data to clipboard" 
Paste into config.env


known issues: sometimes it doesn't scroll to the bottom. rerun the script.
sometimes it will try to grab ad videos. 

i don't do this professionally. is just hobby.

also. be patient. sometimes it takes a long time to finish the infinite scroll for thousands of links

kthxbye
