# 🛡️ Cyber Threat Intelligence Feed

[![Website status](https://img.shields.io/website?url=https%3A%2F%2Fmerv3guler.github.io%2Fcyber-news-feed&label=Website&style=flat-square&color=2ea44f)](https://merv3guler.github.io/cyber-news-feed)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![AI Powered](https://img.shields.io/badge/AI-Gemini%201.5%20Flash-orange?style=flat-square&logo=google)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

**A fully automated, serverless Threat Intelligence Aggregator that collects, analyzes, and summarizes the latest cybersecurity news using Artificial Intelligence.**

> *View the live dashboard here:* [**merv3guler.github.io/cyber-news-feed**](https://merv3guler.github.io/cyber-news-feed)

---

## 🚀 About The Project

Staying updated with the latest vulnerabilities (CVEs), exploits, and cyber attacks is crucial but time-consuming. This project automates the "morning coffee routine" of a Cyber Threat Intelligence (CTI) analyst.

It scrapes trusted sources like **Google Project Zero**, **SANS ISC**, and **The Hacker News**, uses **Google Gemini 1.5 Flash AI** to summarize technical details, and presents them in a modern, Cyberpunk-themed dashboard.

**Key Capabilities:**
* **No Servers:** Runs entirely on GitHub Actions (Free Tier).
* **No Database:** Uses a smart JSON-based storage system to maintain history.
* **AI Analysis:** Summarizes clickbait titles into actionable technical intelligence.

## ✨ Features

* **🤖 AI-Powered Summaries:** Articles are analyzed by Google Gemini to produce concise, technical summaries (Max 50 words).
* **🕵️‍♂️ Zero-Day Detection:** Automatically flags keywords like "0-day", "exploit", and "critical vulnerability" with a visual warning.
* **🔍 Dynamic Filtering:** Filter news by specific sources (e.g., show only *Google Project Zero* or *CISA*).
* **📄 Excel Export:** One-click export feature to download the intelligence report as a `.csv` file.
* **📚 Pagination:** Clean interface with pagination to browse through historical data easily.
* **🌗 Dark/Light Mode:** Cyberpunk aesthetic by default, with a toggle for Light Mode.
* **📱 Social Sharing:** Share critical alerts directly to WhatsApp, LinkedIn, X (Twitter), or Email.

## 📡 Intelligence Sources

The feed aggregates data from the following industry-standard sources:

* **Google Online Security Blog** & **Project Zero**
* **CISA Alerts** (US-CERT)
* **SANS Internet Storm Center**
* **The Hacker News** & **BleepingComputer**
* **Krebs on Security** & **Schneier on Security**
* **Palo Alto Unit 42** & **Trend Micro Research**
* **The Register (Security)**
* **Dark Reading** & **Threatpost**
* **Exploit-DB**

## 🛠️ Installation & Setup

You can deploy your own instance of this tool in **5 minutes** for free.

### 1. Fork the Repository
Click the "Fork" button at the top right of this repository to create your own copy.

### 2. Get a Free Gemini API Key
* Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
* Create a free API key.

### 3. Add Secrets to GitHub
* Go to your forked repo: `Settings` > `Secrets and variables` > `Actions`.
* Click **New repository secret**.
* **Name:** `GEMINI_API_KEY`
* **Value:** (Paste your Google API key here).

### 4. Enable GitHub Pages
* Go to `Settings` > `Pages`.
* Under **Build and deployment**, select **Source** as `Deploy from a branch`.
* Select the branch `main` (or `master`) and folder `/ (root)`.
* Click **Save**.

### 5. Run the Workflow manually (First Time)
* Go to the `Actions` tab.
* Select **Daily Cyber Update** from the left sidebar.
* Click **Run workflow**.
* *Note: The system will now run automatically every day at 08:00 UTC.*

## ⚙️ Configuration

You can customize the `main.py` file to add more RSS feeds or change the AI behavior:

```python
# Add your favorite RSS feeds here
RSS_FEEDS = [
    "[https://your-favorite-security-blog.com/feed](https://your-favorite-security-blog.com/feed)",
    ...
]
