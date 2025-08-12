import os
import time
import random
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

LOCATIONS = ["Islamabad", "Lahore", "Karachi", "London", "New York"]
MAX_PAGES = 5
DELAY_RANGE = (3, 6)
OUTPUT_CSV = "booking_hotels_all.csv"
IMAGE_FOLDER = "images"

def make_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def safe_text(el):
    try:
        return el.text.strip()
    except:
        return ""

def scrape_page(driver, location_name):
    hotels = []
    card_selectors = [
        "div[data-testid='property-card']",
        "div.sr_property_block",
        "div[data-testid='property-card-wrapper']"
    ]
    cards = []
    for sel in card_selectors:
        cards = driver.find_elements(By.CSS_SELECTOR, sel)
        if cards:
            break

    for card in cards:
        try:
            name = ""
            try:
                name = card.find_element(By.CSS_SELECTOR, "div[data-testid='title']").text.strip()
            except:
                try:
                    name = card.find_element(By.CSS_SELECTOR, "h3").text.strip()
                except:
                    name = safe_text(card)

            price = ""
            for ps in [
                "span[data-testid='price-and-discounted-price']",
                ".bui-price-display__value",
                ".price"
            ]:
                try:
                    price = card.find_element(By.CSS_SELECTOR, ps).text.strip()
                    if price:
                        break
                except:
                    pass

            location = ""
            try:
                location = card.find_element(By.CSS_SELECTOR, "span[data-testid='address']").text.strip()
            except:
                try:
                    location = card.find_element(By.CSS_SELECTOR, ".address").text.strip()
                except:
                    location = ""

            rating = ""
            try:
                rating = card.find_element(By.CSS_SELECTOR, "div[data-testid='review-score'] div").text.strip()
            except:
                try:
                    rating = card.find_element(By.CSS_SELECTOR, ".bui-review-score__badge").text.strip()
                except:
                    rating = ""

            img_url = ""
            try:
                img_el = card.find_element(By.CSS_SELECTOR, "img")
                img_url = img_el.get_attribute("src") or img_el.get_attribute("data-src") or ""
            except:
                pass

            page_url = ""
            try:
                a = card.find_element(By.CSS_SELECTOR, "a")
                page_url = a.get_attribute("href") or ""
            except:
                pass

            hotels.append({
                "search_location": location_name,
                "name": name,
                "price": price,
                "location": location,
                "rating": rating,
                "image_url": img_url,
                "page_url": page_url
            })
        except Exception as e:
            print("Card parse error:", e)

    return hotels

def go_to_search(driver, location):
    base = "https://www.booking.com/searchresults.en-gb.html"
    url = f"{base}?ss={location}"
    driver.get(url)
    time.sleep(4)

def click_next_page(driver):
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next page']")
        driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", next_btn)
        return True
    except:
        try:
            next_link = driver.find_element(By.CSS_SELECTOR, "a[rel='next']")
            driver.execute_script("arguments[0].click();", next_link)
            return True
        except:
            return False

def download_images(hotels):
    if not os.path.exists(IMAGE_FOLDER):
        os.makedirs(IMAGE_FOLDER)

    for i, hotel in enumerate(hotels, start=1):
        img_url = hotel.get("image_url", "")
        if img_url:
            try:
                img_data = requests.get(img_url, timeout=10).content
                file_path = os.path.join(IMAGE_FOLDER, f"hotel_{i}.jpg")
                with open(file_path, "wb") as f:
                    f.write(img_data)
                print(f"Downloaded image: {file_path}")
            except Exception as e:
                print(f"Image download failed for {img_url}: {e}")

def main():
    driver = make_driver(headless=True)
    all_hotels = []

    try:
        for city in LOCATIONS:
            print(f"\n--- Scraping for location: {city} ---")
            go_to_search(driver, city)
            current_page = 1

            while current_page <= MAX_PAGES:
                print(f"Scraping page {current_page} for {city}...")
                time.sleep(random.uniform(2.0, 4.0))
                hotels = scrape_page(driver, city)
                print(f"  -> Found {len(hotels)} hotels on this page.")
                all_hotels.extend(hotels)

                time.sleep(random.uniform(*DELAY_RANGE))
                if current_page < MAX_PAGES:
                    clicked = click_next_page(driver)
                    if not clicked:
                        print("No more pages for", city)
                        break
                    time.sleep(random.uniform(4.0, 6.0))
                current_page += 1

        if all_hotels:
            df = pd.DataFrame(all_hotels)
            df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
            print(f"\nSaved {len(df)} rows to {OUTPUT_CSV}")
            download_images(all_hotels)
        else:
            print("No data scraped.")

    except Exception as e:
        print("Fatal error:", e)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
