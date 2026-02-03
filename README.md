# Roblox Account Automation & Follower Tool

This repository contains a Python-based automation suite designed to streamline the creation of Roblox accounts, verify them using temporary emails, and automatically follow a target user. It leverages **Selenium** for browser automation and **NopeCHA** for seamless CAPTCHA solving.

---

## 🚀 Features

* **Automated Signup:** Generates accounts using a customizable prefix and incremental numbering.
* **CAPTCHA Solving:** Integrated support for the [NopeCHA](https://nopecha.com/) browser extension to bypass functional challenges.
* **Email Verification:** Automatically creates temporary mailboxes via [Mail.tm](https://mail.tm/) to verify accounts.
* **Auto-Follow System:** Navigates to a specified Roblox User ID and performs a follow action post-creation.
* **Multi-Threading:** Supports running up to 10 parallel browser instances to accelerate account generation.
* **Discord Integration:** Sends account credentials (Username:Password) and activity logs to a Discord Webhook.
* **Local Logging:** Appends all successfully created accounts to a local `accounts.txt` file.

---

## 🛠️ Prerequisites

Before running the script, ensure you have the following installed:

* **Python 3.8+**
* **Google Chrome:** Installed at the default path: `C:\Program Files\Google\Chrome\Application\chrome.exe`.
* **Dependencies:** Install required packages via pip:
```bash
pip install -r requirements.txt

```



---

## ⚙️ Configuration (`settings.ini`)

Edit the `settings.ini` file to customize the bot's behavior:

| Setting | Description |
| --- | --- |
| **UserPrefix** | The base name for generated accounts (e.g., `WilliamVial`). |
| **NextUsernameNumber** | The starting number for the incrementing suffix. |
| **SignupPassword** | The static password assigned to all new accounts. |
| **NopeCHAKey** | Your API key from [nopecha.com](https://nopecha.com). |
| **DiscordWebhookUrl** | Your Discord server webhook for real-time notifications. |
| **FollowUser** | Set to `true` to follow a profile after signup. |
| **UserId** | The Roblox ID of the profile to be followed. |
| **ThreadCount** | Number of parallel browser instances (1–10). |

---

## 📂 File Structure

* `open_chrome_roblox.py`: The core automation logic and Selenium controller.
* `Execute.bat`: A convenience script to launch the automation with Administrator privileges.
* `settings.ini`: Configuration file for user-specific variables.
* `requirements.txt`: List of necessary Python libraries.
* `accounts.txt`: (Auto-generated) A database of created account credentials.

---

## 🏁 Getting Started

1. **Configure:** Update `settings.ini` with your desired settings and NopeCHA key.
2. **Initialize:** Run `Execute.bat` to start the process.
* *Note: The script will automatically download the latest NopeCHA extension if not found.*


3. **Monitor:** Watch the console for status updates or check your Discord channel for incoming account details.

---

## ⚠️ Disclaimer

This tool is for educational purposes only. Automating account creation may violate Roblox's Terms of Service. Use responsibly and at your own risk.
