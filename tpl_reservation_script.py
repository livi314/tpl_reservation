#!/usr/bin/env python3
import os
import time
import calendar
import pytz
from datetime import datetime, time as dt_time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
import getpass
import argparse

TARGET_ATTRACTIONS = [
    "Ripley's Aquarium",
    "Ripley's Aquarium of Canada",
    "Toronto Zoo"
]

def setup_driver(headless=True):
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    if headless:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
    profile_path = os.path.expanduser("~/.tpl_selenium_profile")
    if os.path.exists(profile_path):
        options.add_argument(f"user-data-dir={profile_path}")
    service = Service('/usr/local/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(20)
    return driver

def create_env_file():
    env_path = Path.home() / ".tpl_credentials.env"
    if not env_path.exists():
        print("First-time setup: Please enter your credentials")
        library_card = input("Enter your library card number: ")
        pin = getpass.getpass("Enter your PIN: ")
        with open(env_path, "w") as f:
            f.write(f"TPL_LIBRARY_CARD={library_card}\n")
            f.write(f"TPL_PIN={pin}\n")
        os.chmod(env_path, 0o600)
        print("Credentials stored securely!")
    return env_path


def load_credentials():
    # First try environment variables (used in GitHub Actions)
    library_card = os.getenv("TPL_LIBRARY_CARD")
    pin = os.getenv("TPL_PIN")
    if library_card and pin:
        return library_card, pin

    # Fallback to local .env file for local runs
    env_path = Path.home() / ".tpl_credentials.env"
    if not env_path.exists():
        env_path = create_env_file()
        print("Credentials saved. Please re-run the script to continue with reservations.")
        exit(0)

    credentials = {}
    with open(env_path, "r") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                credentials[key] = value

    return credentials.get("TPL_LIBRARY_CARD"), credentials.get("TPL_PIN")


def quick_login(driver, library_card, pin):
    try:
        card_input = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.ID, "ePASSPatronNumber"))
        )
        card_input.send_keys(library_card)
        pin_input = WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.ID, "ePASSPatronPassword"))
        )
        pin_input.send_keys(pin)
        login_button = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.ID, "ePASSButtonLogin"))
        )
        login_button.click()
        return True
    except Exception as e:
        print(f"Login failed: {str(e)}")
        return False

def get_next_month(year, month):
    return (year + 1, 1) if month == 12 else (year, month + 1)

def get_first_wednesday(year, month):
    for day in range(1, 8):
        if datetime(year, month, day).weekday() == 2:
            return datetime(year, month, day)
    raise Exception("No Wednesday found in first 7 days")

def get_weekend_dates(year, month):
    weekends = []
    cal = calendar.Calendar()
    for week in cal.monthdatescalendar(year, month):
        for d in week:
            if d.month == month and d.weekday() in (5, 6):
                weekends.append(d.strftime("%Y-%m-%d"))
    return weekends

def wait_until_open(year, month):
    est = pytz.timezone("America/Toronto")
    first_wed = get_first_wednesday(year, month)
    open_time = est.localize(datetime.combine(first_wed, dt_time(14, 0)))
    now = datetime.now(est)
    if now < open_time:
        wait_seconds = (open_time - now).total_seconds()
        print(f"Waiting until {open_time} EST ({wait_seconds/60:.1f} minutes)...")
        time.sleep(max(0, wait_seconds))

def select_date_and_reserve(driver, event_name, test_date):
    from datetime import datetime as dt
    dt_obj = dt.strptime(test_date, "%Y-%m-%d")
    year, month, day = dt_obj.year, dt_obj.month - 1, dt_obj.day
    try:
        date_picker = WebDriverWait(driver, 1).until(
            EC.element_to_be_clickable((By.ID, "ePASSMainDateDisplay"))
        )
        date_picker.click()
        day_selector = f"td[data-month='{month}'][data-year='{year}'] a[data-date='{day}']"
        day_elem = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, day_selector))
        )
        day_elem.click()
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ePASSAttractionName"))
        )
        event_blocks = driver.find_elements(By.CSS_SELECTOR, ".ePASSAttractionListing")
        for event_block in event_blocks:
            try:
                name_el = event_block.find_element(By.CSS_SELECTOR, ".ePASSAttractionName")
                if event_name.lower() in name_el.text.lower():
                    offer_blocks = event_block.find_elements(By.CSS_SELECTOR, "[id^='ePASSOfferDiv']")
                    for offer in offer_blocks:
                        try:
                            date_span = offer.find_element(By.CSS_SELECTOR, ".ePASSCurrentDate.ePASSDateSelection")
                            offer_date_str = date_span.text.strip()
                            offer_date = dt.strptime(offer_date_str, "%B %d, %Y")
                            if offer_date.date() == dt_obj.date():
                                reserve_btn = offer.find_element(
                                    By.XPATH,
                                    ".//input[@type='button' and @value='Reserve' and contains(@class, 'ePASSReserveButton')]"
                                )
                                driver.execute_script("arguments[0].scrollIntoView(true);", reserve_btn)
                                reserve_btn.click()
                                try:
                                    continue_btn = WebDriverWait(driver, 1).until(
                                        EC.element_to_be_clickable((By.ID, "ePASSContinueButton"))
                                    )
                                    continue_btn.click()
                                except Exception:
                                    return False
                                try:
                                    WebDriverWait(driver, 1).until(
                                        EC.visibility_of_element_located((By.XPATH, "//h1[contains(text(), 'My Reservations')]"))
                                    )
                                    return True
                                except Exception:
                                    return False
                        except Exception:
                            continue
            except Exception:
                continue
    except Exception as e:
        print(f"Error in select_date_and_reserve: {e}")
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["monthly", "daily"], default="monthly", help="Run mode: monthly or daily")
    args = parser.parse_args()

    library_card, pin = load_credentials()
    if not library_card or not pin:
        print("Error: Credentials not found")
        return

    est = pytz.timezone("America/Toronto")
    now = datetime.now(est)
    year, month = now.year, now.month
    target_year, target_month = get_next_month(year, month)

    if args.mode == "monthly":
        if now.date() != get_first_wednesday(year, month).date():
            print("Today is not the first Wednesday of the month. Exiting.")
            return
        wait_until_open(year, month)
        weekends = get_weekend_dates(target_year, target_month)
    else:
        weekends = get_weekend_dates(year, month) + get_weekend_dates(target_year, target_month)

    print(f"Target weekends for reservation: {weekends}")
    reserved = {}

    end_time = now.replace(minute=10, second=0) if args.mode == "monthly" else now.replace(minute=59, second=59)

    while datetime.now(est) < end_time and len(reserved) < len(weekends):
        for date in weekends:
            if date in reserved:
                continue
            driver = None
            try:
                driver = setup_driver(headless=True)
                driver.get("https://epass-ca.quipugroup.net/?clientID=16&libraryID=1")
                if not quick_login(driver, library_card, pin):
                    print("Login failed, will retry...")
                    continue
                for attraction in TARGET_ATTRACTIONS:
                    if select_date_and_reserve(driver, attraction, date):
                        print(f"Reserved {attraction} for {date}!")
                        reserved[date] = attraction
                        break
            except Exception as e:
                print(f"Error for {date}: {e}")
            finally:
                if driver:
                    driver.quit()
                time.sleep(2)
        if len(reserved) < len(weekends):
            print("Some dates not reserved yet, retrying soon...")
            time.sleep(3)

    print("Reservation results:")
    for date in weekends:
        if date in reserved:
            print(f"{date}: {reserved[date]}")
        else:
            print(f"{date}: NOT RESERVED")

if __name__ == "__main__":
    main()
