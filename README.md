# 🇫🇷 France Visa Slot Auto-Monitor

Automatically monitors the French Embassy in Ireland's visa appointment system for available time slots and sends instant email notifications when one is found.

注意：原始的跑用的是GLM-5， 如果你换成其他模型，跑完一轮以后模型输出的结果内容上面会有一定的差异，最好是通过LLM读一下你的这一轮跑完以后你使用的LLM的输出内容然后根据这个重新调整一下Python里面的关键词，可以显著降低误认为有slot的情况

## ✨ Features

- **Automated Checking** — Uses `agent-browser` to simulate browser interactions and navigate the visa appointment page
- **Smart Detection** — LLM-powered snapshot analysis with multilingual keyword matching (Chinese / English / French)
- **Email Alerts** — Sends email notifications with calendar screenshots when a slot is detected
- **Scheduled Runs** — Checks every 5 minutes for 1 hour (12 iterations per session)

## 📁 Project Structure

```
france/
├── README.md                          # This file
├── scheduled_check.py                 # Main script: scheduled checking + email alerts
├── send_email.py                      # Standalone email sending test script
├── check-visa-slot.md                 # Step-by-step slot checking workflow (for LLM)
├── how-to-get-gmail-app-password.md   # Guide to obtaining a Gmail App Password
├── calendar-result.png               # Calendar page screenshot (generated at runtime)
├── snapshot-*.txt                     # Page snapshots (generated at runtime)
└── visa-slot-result-*.txt            # Check result logs (generated at runtime)
```

## 🛠️ Prerequisites

- **Python 3.x**
- **Node.js** & **npm**
- **Google Chrome**
- **[opencode](https://github.com/opencode-ai/opencode)** CLI — Invokes LLM to execute the checking workflow
- **[agent-browser](https://www.npmjs.com/package/agent-browser)** — Browser automation tool

## 🚀 Getting Started

### 1. Install Dependencies

```bash
# Install agent-browser
npm install -g agent-browser --force
agent-browser install
```

### 2. Configure Email Notifications

1. Enable **2-Step Verification** on your Google account
2. Generate a 16-digit App Password at the [App Passwords page](https://myaccount.google.com/apppasswords)
3. Update the email configuration in `scheduled_check.py`:

```python
SENDER_EMAIL = "your-sender@gmail.com"
RECEIVER_EMAIL = "your-receiver@gmail.com"
APP_PASSWORD = "your-app-password"
```

> For detailed instructions, see [how-to-get-gmail-app-password.md](./how-to-get-gmail-app-password.md)

### 3. Run

```bash
python3 scheduled_check.py
```

The script will check the visa appointment page every 5 minutes for 1 hour. If an available slot is detected, an email notification will be sent automatically.

## ⚙️ How It Works

```
scheduled_check.py
       │
       ▼
  opencode CLI ─── Reads check-visa-slot.md workflow
       │
       ▼
  agent-browser ─── Automates Chrome browser
       │
       ▼
  Visit appointment site → Click through pages → View calendar
       │
       ▼
  LLM analyzes snapshot → Determines slot availability
       │
       ├── Slot found    → 📧 Send email notification
       └── No slot found → 📝 Log result, wait for next check
```

## 📧 Email Notifications

When a potentially available visa slot is detected, the system sends an email containing:

- Timestamp of the check
- Full LLM analysis result
- Calendar page screenshot (as attachment)

## ⚠️ Notes

- **Security** — Do not commit code containing your App Password to public repositories
- **Rate Limiting** — Keep the default 5-minute interval; checking too frequently may get blocked
- **Timezone** — The appointment page uses Irish time (Europe/Dublin, UTC+0)
- **Element References** — Browser element `ref` IDs may change between runs; the LLM handles this automatically

## 📝 License

For personal use only.
