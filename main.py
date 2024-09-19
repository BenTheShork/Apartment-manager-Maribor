import requests
from bs4 import BeautifulSoup
import time
import telebot
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random

# Replace with your Telegram bot token
TELEGRAM_BOT_TOKEN = '7477415221:AAG84JgnOSD8Ivrz1Wy2NmExcTxjx1_swIM'
# Replace with your Telegram chat ID
TELEGRAM_CHAT_ID = '1680103387'

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Files to store the most recent apartments
LAST_APT_FILE_BOLHA = 'last_apartment_bolha.json'
LAST_APT_FILE_NEPREMICNINE = 'last_apartment_nepremicnine.json'

# List of common user agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36 Edg/91.0.864.59'
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def load_last_apartment(file_name):
    try:
        with open(file_name, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_last_apartment(apartment, file_name):
    with open(file_name, 'w') as f:
        json.dump(apartment, f)

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"user-agent={get_random_user_agent()}")
    return webdriver.Chrome(options=chrome_options)

def scroll_page(driver):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(1, 3))
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(random.uniform(1, 3))

def is_apartment_listing_bolha(listing):
    title = listing.find('h3', class_='entity-title').text.strip().lower()
    return 'stanovanje' in title or 'oddaja' in title

def scrape_bolha():
    url = 'https://www.bolha.com/oddaja-stanovanja/maribor'
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        listings = soup.find_all('article', class_='entity-body')
        new_listings = []
        last_apartment = load_last_apartment(LAST_APT_FILE_BOLHA)
        
        for listing in listings:
            if not is_apartment_listing_bolha(listing):
                continue
            
            title = listing.find('h3', class_='entity-title').text.strip()
            link = 'https://www.bolha.com' + listing.find('a', class_='link')['href']
            price = listing.find('strong', class_='price').text.strip() if listing.find('strong', class_='price') else 'Price not specified'
            description = listing.find('div', class_='entity-description-main').text.strip()
            
            location_elem = listing.find('span', class_='entity-description-itemCaption', string='Lokacija: ')
            location = location_elem.find_next(text=True).strip() if location_elem else 'Location not specified'
            
            apartment = {
                'source': 'Bolha',
                'title': title,
                'price': price,
                'location': location,
                'description': description,
                'link': link
            }
            
            if apartment == last_apartment:
                break
            
            new_listings.append(apartment)
        
        if new_listings:
            save_last_apartment(new_listings[0], LAST_APT_FILE_BOLHA)
        return new_listings
    
    except requests.RequestException as e:
        print(f"Error scraping Bolha: {str(e)}")
        return []

def scrape_nepremicnine():
    url = 'https://www.nepremicnine.net/oglasi-oddaja/podravska/maribor/stanovanje/?s=16'
    
    try:
        driver = setup_driver()
        driver.get(url)
        
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "property-box")))
        
        scroll_page(driver)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        listings = soup.find_all('div', class_='property-box property-normal mt-4 mt-md-0')
        
        new_listings = []
        last_apartment = load_last_apartment(LAST_APT_FILE_NEPREMICNINE)
        
        for listing in listings:
            title = listing.find('h2').text.strip()
            link = 'https://www.nepremicnine.net' + listing.find('a', class_='url-title-d')['href']
            price = listing.find('h6').text.strip()
            description = listing.find('p', class_='font-roboto hidden-m').text.strip()
            
            details = listing.find('ul', itemprop='disambiguatingDescription')
            size = details.find('li').text.strip() if details else 'Size not specified'
            location = 'Maribor'
            
            apartment = {
                'source': 'Nepremicnine',
                'title': title,
                'price': price,
                'location': location,
                'description': description,
                'size': size,
                'link': link
            }
            
            if apartment == last_apartment:
                break
            
            new_listings.append(apartment)
        
        if new_listings:
            save_last_apartment(new_listings[0], LAST_APT_FILE_NEPREMICNINE)
        return new_listings
    
    except Exception as e:
        print(f"Error scraping Nepremicnine: {str(e)}")
        return []
    finally:
        driver.quit()

def send_telegram_message(message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as e:
        print(f"Error sending Telegram message: {str(e)}")

def format_apartment_message(apt):
    message = f"Source: {apt['source']}\n"
    message += f"Title: {apt['title']}\n"
    message += f"Price: {apt['price']}\n"
    message += f"Location: {apt['location']}\n"
    if 'size' in apt:
        message += f"Size: {apt['size']}\n"
    message += f"Description: {apt['description']}\n"
    message += f"Link: {apt['link']}"
    return message

def scrape_and_notify():
    bolha_listings = scrape_bolha()
    nepremicnine_listings = scrape_nepremicnine()
    
    all_new_listings = bolha_listings + nepremicnine_listings
    
    if all_new_listings:
        send_telegram_message("New apartments found:")
        for apt in reversed(all_new_listings):
            send_telegram_message(format_apartment_message(apt))
    else:
        print("No new apartments found.")

def main():
    print("Starting the combined apartment scraper...")
    while True:
        scrape_and_notify()
        time.sleep(300 + random.uniform(0, 60))  # Wait for 5-6 minutes before the next scrape

if __name__ == "__main__":
    main()