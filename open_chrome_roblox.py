"""Open Chrome with NopeCHA, go to Roblox signup, and fill form from settings."""
import concurrent.futures
import os
import re
import sys
import tempfile
import threading
import time
import urllib.request
import uuid
import zipfile
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
ROBLOX_SIGNUP = "https://www.roblox.com/signup"
ROBLOX_HOME = "https://www.roblox.com/home"
NOPECHA_EXTENSION_URL = "https://github.com/NopeCHALLC/nopecha-extension/releases/latest/download/chromium.zip"
MAIL_TM_BASE = "https://api.mail.tm"
ROBLOX_VERIFICATION_LINK_PATTERN = re.compile(
    r"https://www\.roblox\.com/account/settings/[^\s\"'<>]+"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_PATH = os.path.join(SCRIPT_DIR, "settings.ini")
ACCOUNTS_FILE = os.path.join(SCRIPT_DIR, "accounts.txt")
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1468082631265751215/3MBxGMo3Erxt9sCifRVbfe6w1Xber9OCiqezUvd9mavhivC-7jgWyy73VPiQS3ufLAmD"
# Use temp dir for extension to avoid OneDrive/virtual-file permission issues
NOPECHA_EXTENSION_DIR = os.path.join(tempfile.gettempdir(), "nopecha_chromium_roblox")

# Thread safety: username counter and accounts file
USERNAME_LOCK = threading.Lock()
ACCOUNTS_LOCK = threading.Lock()


def load_settings():
    """Read all settings from settings.ini."""
    prefix = "user"
    next_num = 1
    password = ""
    nopecha_key = ""
    nopecha_extension_path = ""
    discord_webhook = ""
    follow_user = "false"
    user_id = ""
    loop_count = 1
    thread_count = 3
    if os.path.isfile(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key, value = key.strip(), value.strip()
                    if key == "UserPrefix":
                        prefix = value or prefix
                    elif key == "NextUsernameNumber":
                        try:
                            next_num = max(1, int(value))
                        except ValueError:
                            pass
                    elif key == "SignupPassword":
                        password = value
                    elif key == "NopeCHAKey":
                        nopecha_key = value
                    elif key == "NopeCHAExtensionPath":
                        nopecha_extension_path = value
                    elif key == "DiscordWebhookUrl":
                        discord_webhook = value
                    elif key == "FollowUser":
                        follow_user = value or follow_user
                    elif key == "UserId":
                        user_id = value
                    elif key == "LoopCount":
                        try:
                            loop_count = max(1, int(value))
                        except ValueError:
                            pass
                    elif key == "ThreadCount":
                        try:
                            thread_count = max(1, min(10, int(value)))
                        except ValueError:
                            pass
    return (
        prefix,
        next_num,
        password,
        nopecha_key,
        nopecha_extension_path,
        discord_webhook,
        follow_user,
        user_id,
        loop_count,
        thread_count,
    )


def save_next_number(next_num):
    """Update NextUsernameNumber in settings.ini, keep rest of file intact."""
    lines = []
    if os.path.isfile(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    found = False
    new_lines = []
    for line in lines:
        if line.strip().startswith("NextUsernameNumber="):
            new_lines.append(f"NextUsernameNumber={next_num}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"NextUsernameNumber={next_num}\n")
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def get_next_username():
    """Return prefix + current number, then increment and save for next run. Call under USERNAME_LOCK when using threads."""
    prefix, next_num, _, _, _, _, _, _, _, _ = load_settings()
    username = f"{prefix}{next_num}"
    save_next_number(next_num + 1)
    return username


def get_signup_password():
    """Return password from settings for signup form."""
    return load_settings()[2]


def get_nopecha_key():
    """Return NopeCHA subscription key from settings."""
    return load_settings()[3]


def get_nopecha_extension_path():
    """Return manual path to NopeCHA extension folder from settings (empty = use download/cache)."""
    return load_settings()[4]


def get_discord_webhook_url():
    """Return Discord webhook URL from settings, or default if empty."""
    url = load_settings()[5]
    return url.strip() if url else DISCORD_WEBHOOK_URL


def get_follow_user_enabled():
    """Return True if FollowUser is set to true (case-insensitive)."""
    return load_settings()[6].lower() == "true"


def get_follow_user_id():
    """Return UserId from settings (Roblox user ID to follow)."""
    return load_settings()[7].strip()


def get_loop_count():
    """Return how many times to run the signup cycle (from LoopCount in settings)."""
    return load_settings()[8]


def get_thread_count():
    """Return how many threads to run in parallel (from ThreadCount in settings, 1–10)."""
    return load_settings()[9]


def save_account_and_notify(username, password):
    """Append account to accounts.txt (Username:Password:Date Created) and send to Discord webhook. Thread-safe."""
    with ACCOUNTS_LOCK:
        date_created = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"{username}:{password}:{date_created}\n"
        with open(ACCOUNTS_FILE, "a", encoding="utf-8") as f:
            f.write(line)
        webhook_url = get_discord_webhook_url()
        payload = {
            "embeds": [
                {
                    "title": "New Roblox Account",
                    "color": 0x00AEFF,
                    "fields": [
                        {"name": "Username", "value": username, "inline": True},
                        {"name": "Password", "value": password, "inline": True},
                        {"name": "Date Created", "value": date_created, "inline": True},
                    ],
                }
            ]
        }
        try:
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            print(f"Discord webhook failed: {e}", file=sys.stderr)


def follow_user_profile(driver, wait):
    """If FollowUser is true, go to user profile, click Follow, and notify webhook with followed username."""
    if not get_follow_user_enabled():
        return
    user_id = get_follow_user_id()
    if not user_id:
        return
    profile_url = f"https://www.roblox.com/users/{user_id}/profile"
    driver.get(profile_url)
    wait.until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    # Get profile username from span.stylistic-alts-username (e.g. The_HippoGamer)
    try:
        username_el = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "span.stylistic-alts-username")
            )
        )
        profile_username = username_el.text.strip()
        if profile_username and not profile_username.startswith("@"):
            profile_username = f"@{profile_username}"
    except Exception:
        profile_username = f"@{user_id}"

    # Open contextual menu (three dots)
    menu_btn = wait.until(
        EC.element_to_be_clickable(
            (By.ID, "user-profile-header-contextual-menu-button")
        )
    )
    menu_btn.click()

    # Click Follow in the menu
    follow_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[.//span[contains(@class,'foundation-web-menu-item-title') and text()='Follow']]")
        )
    )
    follow_btn.click()

    # Notify webhook: "Followed user @username"
    webhook_url = get_discord_webhook_url()
    payload = {
        "content": f"Followed user {profile_username}",
    }
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except Exception as e:
        print(f"Discord webhook (follow) failed: {e}", file=sys.stderr)


def create_temp_email():
    """Create a mail.tm temp email account; return (email_address, auth_headers)."""
    username = uuid.uuid4().hex[:10]
    domains_resp = requests.get(f"{MAIL_TM_BASE}/domains", timeout=30)
    domains_resp.raise_for_status()
    domains = domains_resp.json()["hydra:member"]
    domain = domains[0]["domain"]
    email = f"{username}@{domain}"
    password = "Password123!"
    requests.post(
        f"{MAIL_TM_BASE}/accounts",
        json={"address": email, "password": password},
        timeout=30,
    ).raise_for_status()
    token_resp = requests.post(
        f"{MAIL_TM_BASE}/token",
        json={"address": email, "password": password},
        timeout=30,
    )
    token_resp.raise_for_status()
    token = token_resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    return email, headers


def poll_for_roblox_verification_link(headers):
    """Poll mail.tm inbox until a message contains a Roblox account/settings link; return that link."""
    while True:
        resp = requests.get(f"{MAIL_TM_BASE}/messages", headers=headers, timeout=30)
        resp.raise_for_status()
        messages = resp.json().get("hydra:member", [])
        for msg in messages:
            msg_id = msg["id"]
            full = requests.get(
                f"{MAIL_TM_BASE}/messages/{msg_id}", headers=headers, timeout=30
            ).json()
            content = f"{full.get('text', '')} {full.get('html', '')}"
            links = ROBLOX_VERIFICATION_LINK_PATTERN.findall(content)
            if links:
                return links[0]
        time.sleep(5)


def _extension_path_with_manifest(base):
    """Return base if it contains manifest.json, else first subdir that does."""
    manifest_path = os.path.join(base, "manifest.json")
    if os.path.isfile(manifest_path):
        return base
    try:
        for name in os.listdir(base):
            sub = os.path.join(base, name)
            if os.path.isdir(sub):
                found = _extension_path_with_manifest(sub)
                if found:
                    return found
    except OSError:
        pass
    return None


def ensure_nopecha_extension():
    """Use NopeCHA extension from settings path, cache, or download; return path to extension dir."""
    manual_path = get_nopecha_extension_path().strip()
    if manual_path and os.path.isdir(manual_path):
        path = _extension_path_with_manifest(manual_path)
        if path:
            return path
        raise FileNotFoundError(
            f"NopeCHAExtensionPath does not contain manifest.json: {manual_path}"
        )

    if os.path.isdir(NOPECHA_EXTENSION_DIR):
        path = _extension_path_with_manifest(NOPECHA_EXTENSION_DIR)
        if path:
            return path

    try:
        os.makedirs(NOPECHA_EXTENSION_DIR, exist_ok=True)
        zip_path = os.path.join(tempfile.gettempdir(), "nopecha_chromium_roblox.zip")
        print("Downloading NopeCHA extension...")
        with urllib.request.urlopen(NOPECHA_EXTENSION_URL, timeout=60) as response:
            with open(zip_path, "wb") as f:
                f.write(response.read())
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(NOPECHA_EXTENSION_DIR)
        try:
            os.remove(zip_path)
        except OSError:
            pass
    except (PermissionError, OSError) as e:
        print(
            "\nCould not download NopeCHA extension (permission/network error).\n"
            "Use a manual path instead:\n"
            "1. Download: https://github.com/NopeCHALLC/nopecha-extension/releases/latest/download/chromium.zip\n"
            "2. Extract the zip to a folder (e.g. C:\\nopecha_chromium).\n"
            "3. In settings.ini set: NopeCHAExtensionPath=C:\\nopecha_chromium\n"
            "   (use the folder that contains manifest.json, or its parent if manifest is in a subfolder)\n",
            file=sys.stderr,
        )
        raise SystemExit(1) from e

    path = _extension_path_with_manifest(NOPECHA_EXTENSION_DIR)
    if not path:
        raise FileNotFoundError("NopeCHA extension missing manifest.json after extract")
    return path


def _chrome_options(user_data_dir, extension_path):
    """Build Chrome options for a single driver instance."""
    options = Options()
    options.binary_location = CHROME_PATH
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--load-extension=" + extension_path)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-gpu-sandbox")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-gpu-compositing")
    options.add_argument("--disable-gpu-rasterization")
    options.add_argument("--disable-gpu-shader-disk-cache")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--remote-debugging-port=0")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    return options


def do_one_cycle(driver, wait, username, password):
    """Run one full account cycle: signup -> verify -> save -> follow -> logout. Uses given username/password."""
    driver.get(ROBLOX_SIGNUP)

    month_select = wait.until(
        EC.presence_of_element_located((By.ID, "MonthDropdown"))
    )
    Select(month_select).select_by_value("Jan")
    day_select = driver.find_element(By.ID, "DayDropdown")
    Select(day_select).select_by_value("13")
    year_select = driver.find_element(By.ID, "YearDropdown")
    Select(year_select).select_by_value("2000")

    username_field = wait.until(
        EC.presence_of_element_located((By.ID, "signup-username"))
    )
    username_field.clear()
    username_field.send_keys(username)
    password_field = driver.find_element(By.ID, "signup-password")
    password_field.clear()
    password_field.send_keys(password)

    male_btn = driver.find_element(By.ID, "MaleButton")
    male_btn.click()
    signup_btn = driver.find_element(By.ID, "signup-button")
    signup_btn.click()

    wait.until(EC.url_contains("roblox.com/home"))
    wait.until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

    add_email_btn = wait.until(
        EC.element_to_be_clickable((By.ID, "upsell-card-secondary-button"))
    )
    add_email_btn.click()

    email_input = wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input.verification-upsell-modal-input")
        )
    )
    email_input.click()
    temp_email, mail_headers = create_temp_email()
    print(f"[{username}] Temp email: {temp_email}")
    email_input.clear()
    email_input.send_keys(temp_email)

    submit_btn = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//div[contains(@class,'modal')]//button[contains(.,'Continue') or contains(.,'Send') or contains(.,'Verify') or contains(.,'Submit')]",
            )
        )
    )
    submit_btn.click()

    print(f"[{username}] Waiting for verification email...")
    verification_link = poll_for_roblox_verification_link(mail_headers)
    print(f"[{username}] Opening verification link.")
    driver.get(verification_link)

    save_account_and_notify(username, password)
    print(f"[{username}] Saved and sent to Discord.")

    follow_user_profile(driver, wait)

    settings_cog = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.btn-navigation-nav-settings-md")
        )
    )
    settings_cog.click()
    logout_link = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.logout-menu-item"))
    )
    logout_link.click()


def run_one_account_generation(cycle_index):
    """Run one account generation in a separate Chrome instance. Thread-safe username allocation."""
    with USERNAME_LOCK:
        username = get_next_username()
        password = get_signup_password()
    extension_path = ensure_nopecha_extension()
    user_data_dir = os.path.join(
        tempfile.gettempdir(), f"roblox_signup_chrome_{uuid.uuid4().hex[:8]}"
    )
    options = _chrome_options(user_data_dir, extension_path)
    driver = None
    try:
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"[{cycle_index + 1}] Chrome failed: {e}", file=sys.stderr)
        return
    try:
        nopecha_key = get_nopecha_key()
        if nopecha_key:
            driver.get(f"https://nopecha.com/setup#{nopecha_key}")
        wait = WebDriverWait(driver, 15)
        do_one_cycle(driver, wait, username, password)
    finally:
        if driver:
            driver.quit()


def main():
    ensure_nopecha_extension()
    loop_count = get_loop_count()
    thread_count = get_thread_count()
    print(f"Running {loop_count} account(s) with {thread_count} thread(s) in parallel.")

    with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [
            executor.submit(run_one_account_generation, i) for i in range(loop_count)
        ]
        for fut in concurrent.futures.as_completed(futures):
            try:
                fut.result()
            except Exception as e:
                print(f"Worker error: {e}", file=sys.stderr)

    print(f"Completed {loop_count} account(s).")
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
