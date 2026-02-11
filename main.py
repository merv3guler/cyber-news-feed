import os
import feedparser
import pytz
from datetime import datetime, timedelta
from jinja2 import Template
import google.generativeai as genai
import time
import json
import re

# --- CONFIGURATION ---
RSS_FEEDS = [
    # Global Cybersecurity News
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.theregister.com/security/headlines.atom",
    
    # Official Alerts & Government Advisories
    "https://www.cisa.gov/uscert/ncas/alerts.xml",
    "https://isc.sans.edu/rssfeed_full.xml", # SANS Internet Storm Center
    
    # Threat Intelligence & Deep Dive Research
    "https://krebsonsecurity.com/feed/",
    "https://www.schneier.com/feed/atom/", # Bruce Schneier
    "https://googleprojectzero.blogspot.com/feeds/posts/default", # Google Project Zero (Deep Technical)
    "https://blog.trendmicro.com/category/trendlabs-security-intelligence/feed/",
    
    # Vulnerabilities, Exploits & Patch Management
    "https://www.darkreading.com/rss.xml",
    "https://threatpost.com/feed/"
]

GITHUB_PROFILE = "https://github.com/merv3guler"
DATA_FILE = "data/articles.json"

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cyber Threat Intel | Merve Guler</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        :root {
            /* DARK MODE (DEFAULT) */
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --text-main: #c9d1d9;
            --text-muted: #8b949e;
            --border: #30363d;
            --accent: #00ff41; /* MATRIX GREEN */
            --accent-glow: rgba(0, 255, 65, 0.2);
            --danger: #ff003c;
            --sun-color: #f39c12; /* ORANGE/YELLOW SUN */
        }

        /* LIGHT MODE VARIABLES */
        body.light-mode {
            --bg-color: #f6f8fa;
            --card-bg: #ffffff;
            --text-main: #24292f;
            --text-muted: #57606a;
            --border: #d0d7de;
            --accent: #1f883d;
            --accent-glow: rgba(31, 136, 61, 0.1);
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            transition: background-color 0.3s, color 0.3s;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        /* HEADER */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 20px;
        }

        h1 {
            font-family: 'JetBrains Mono', monospace;
            color: var(--accent);
            margin: 0;
            font-size: 1.8rem;
            text-shadow: 0 0 5px var(--accent-glow);
        }

        .header-controls {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .icon-btn {
            background: none;
            border: 1px solid var(--border);
            color: var(--text-main);
            padding: 8px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1.1rem;
            transition: all 0.2s;
        }

        .icon-btn:hover {
            border-color: var(--accent);
            color: var(--accent);
            box-shadow: 0 0 10px var(--accent-glow);
        }

        /* SUN ICON SPECIFIC */
        .fa-sun {
            color: var(--sun-color);
            filter: drop-shadow(0 0 3px var(--sun-color));
        }

        /* CONTROLS BAR */
        .controls-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 30px;
            justify-content: space-between;
            align-items: center;
        }

        .filters {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .filter-btn {
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 6px 12px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.85rem;
            font-family: 'JetBrains Mono', monospace;
            transition: 0.2s;
        }

        .filter-btn:hover, .filter-btn.active {
            background-color: var(--accent);
            color: #000;
            border-color: var(--accent);
            font-weight: bold;
        }
        
        .filter-btn.zeroday-btn {
            border-color: var(--danger);
            color: var(--danger);
        }
        
        .filter-btn.zeroday-btn:hover, .filter-btn.zeroday-btn.active {
            background-color: var(--danger);
            color: #fff;
        }

        .export-btn {
            background-color: var(--card-bg);
            border: 1px solid var(--accent);
            color: var(--accent);
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .export-btn:hover {
            background-color: var(--accent);
            color: #000;
        }

        /* GRID */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 20px;
        }

        /* CARD */
        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            position: relative;
            transition: transform 0.2s;
            overflow: hidden;
        }

        .card:hover {
            transform: translateY(-3px);
            border-color: var(--accent);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }

        .zeroday-banner {
            background-color: var(--danger);
            color: #fff;
            font-size: 0.7rem;
            font-weight: bold;
            padding: 4px 8px;
            position: absolute;
            top: 0;
            right: 0;
            border-bottom-left-radius: 8px;
            animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }

        .meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            font-size: 0.8rem;
            font-family: 'JetBrains Mono', monospace;
        }

        .source-badge {
            background-color: #21262d;
            border: 1px solid var(--border);
            padding: 2px 8px;
            border-radius: 4px;
            color: var(--accent);
        }
        
        body.light-mode .source-badge {
            background-color: #eef1f4;
        }

        h2 {
            font-size: 1.1rem;
            margin: 0 0 10px 0;
            line-height: 1.4;
        }

        h2 a {
            color: var(--text-main);
            text-decoration: none;
            transition: color 0.2s;
        }

        h2 a:hover {
            color: var(--accent);
        }

        .summary {
            font-size: 0.9rem;
            line-height: 1.5;
            color: var(--text-muted);
            margin-bottom: 20px;
            flex-grow: 1;
        }

        /* SHARE BUTTONS */
        .card-footer {
            border-top: 1px solid var(--border);
            padding-top: 15px;
            display: flex;
            justify-content: flex-end;
            gap: 15px;
        }

        .share-icon {
            color: var(--text-muted);
            font-size: 1.1rem;
            text-decoration: none;
            transition: 0.2s;
        }

        .share-icon:hover {
            color: var(--accent);
            transform: scale(1.1);
        }
        
        .share-icon:hover .fa-x-twitter {
            color: var(--text-main);
        }

        footer {
            margin-top: 50px;
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
            padding-bottom: 20px;
        }

        .heart { color: #ff003c; animation: beat 1s infinite alternate; display: inline-block; }
        @keyframes beat { to { transform: scale(1.1); } }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div>
            <h1>/// CYBER_INTEL_FEED</h1>
            <small style="font-family: 'JetBrains Mono'; color: var(--text-muted);">
                System Status: <span style="color:var(--accent)">ONLINE</span> | {{ last_updated }}
            </small>
        </div>
        <div class="header-controls">
            <button class="icon-btn" id="themeToggle" title="Toggle Theme">
                <i class="fas fa-sun"></i>
            </button>
            <a href="{{ github_profile }}" target="_blank" class="icon-btn" title="GitHub Profile">
                <i class="fab fa-github"></i>
            </a>
        </div>
    </header>

    <div class="controls-bar">
        <div class="filters" id="filterContainer">
            <button class="filter-btn active" onclick="filterNews('all')">All</button>
            <button class="filter-btn zeroday-btn" onclick="filterNews('zeroday')">Zero Day</button>
        </div>
        <button class="export-btn" onclick="exportToExcel()">
            <i class="fas fa-file-excel"></i> Export Report
        </button>
    </div>

    <div class="grid" id="newsGrid">
        {% for item in items %}
        <article class="card" data-source="{{ item.source }}" data-zeroday="{{ 'true' if item.is_zeroday else 'false' }}">
            {% if item.is_zeroday %}
            <div class="zeroday-banner">⚠️ ZERO-DAY DETECTED</div>
            {% endif %}
            
            <div class="meta">
                <span class="source-badge">{{ item.source }}</span>
                <span>{{ item.date }}</span>
            </div>
            
            <h2><a href="{{ item.link }}" target="_blank">{{ item.title }}</a></h2>
            
            <div class="summary">
                {{ item.summary | safe }}
            </div>

            <div class="card-footer">
                <a href="https://wa.me/?text=Check this out: {{ item.link }}" target="_blank" class="share-icon" title="Share on WhatsApp">
                    <i class="fab fa-whatsapp"></i>
                </a>
                <a href="https://www.linkedin.com/sharing/share-offsite/?url={{ item.link }}" target="_blank" class="share-icon" title="Share on LinkedIn">
                    <i class="fab fa-linkedin"></i>
                </a>
                <a href="https://twitter.com/intent/tweet?text=Cyber Security Alert: {{ item.title }}&url={{ item.link }}" target="_blank" class="share-icon" title="Share on X">
                    <i class="fa-brands fa-x-twitter"></i>
                </a>
                <a href="mailto:?subject=Cyber Intelligence Report&body=I thought this might interest you: {{ item.title }} - {{ item.link }}" class="share-icon" title="Send via Email">
                    <i class="fas fa-envelope"></i>
                </a>
            </div>
        </article>
        {% endfor %}
    </div>

    <footer>
        Developed by <a href="{{ github_profile }}" style="color:var(--text-main);text-decoration:none;font-weight:bold;">Merve Guler</a> 
        <span class="heart">🩷</span>
    </footer>
</div>

<script>
    // --- 1. DARK/LIGHT MODE ---
    const toggleBtn = document.getElementById('themeToggle');
    const icon = toggleBtn.querySelector('i');
    const body = document.body;

    if (localStorage.getItem('theme') === 'light') {
        body.classList.add('light-mode');
        icon.classList.replace('fa-sun', 'fa-moon');
        icon.style.color = ""; 
    }

    toggleBtn.addEventListener('click', () => {
        body.classList.toggle('light-mode');
        if (body.classList.contains('light-mode')) {
            icon.classList.replace('fa-sun', 'fa-moon');
            icon.style.color = ""; 
            localStorage.setItem('theme', 'light');
        } else {
            icon.classList.replace('fa-moon', 'fa-sun');
            icon.style.color = "#f39c12"; 
            localStorage.setItem('theme', 'dark');
        }
    });

    // --- 2. FILTERS ---
    const cards = document.querySelectorAll('.card');
    const sources = new Set();
    cards.forEach(card => sources.add(card.getAttribute('data-source')));

    const filterContainer = document.getElementById('filterContainer');
    
    Array.from(sources).sort().forEach(source => {
        const btn = document.createElement('button');
        btn.innerText = source;
        btn.className = 'filter-btn';
        btn.onclick = () => filterNews(source);
        filterContainer.appendChild(btn);
    });

    function filterNews(criteria) {
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        cards.forEach(card => {
            const source = card.getAttribute('data-source');
            const isZeroDay = card.getAttribute('data-zeroday') === 'true';

            if (criteria === 'all') {
                card.style.display = 'flex';
            } else if (criteria === 'zeroday') {
                card.style.display = isZeroDay ? 'flex' : 'none';
            } else {
                card.style.display = source === criteria ? 'flex' : 'none';
            }
        });
    }

    // --- 3. EXCEL EXPORT ---
    function exportToExcel() {
        let csvContent = "data:text/csv;charset=utf-8,";
        csvContent += "Source,Date,Title,Link,Summary\\n"; 

        cards.forEach(card => {
            if (card.style.display !== 'none') {
                const source = card.getAttribute('data-source');
                const date = card.querySelector('.meta span:last-child').innerText;
                const title = card.querySelector('h2 a').innerText.replace(/,/g, '');
                const link = card.querySelector('h2 a').href;
                const summary = card.querySelector('.summary').innerText.replace(/\\n/g, ' ').replace(/,/g, '');
                
                csvContent += `${source},${date},${title},${link},"${summary}"\\n`;
            }
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "cyber_intel_report.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
</script>

</body>
</html>
"""

def load_existing_articles():
    """Load existing articles from JSON file to keep history."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_articles(articles):
    """Save all articles to JSON file."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

def fetch_news():
    articles = []
    utc_now = datetime.now(pytz.utc)
    # Fetch last 24h
    time_limit = utc_now - timedelta(hours=24)
    
    print("Scanning feeds...")
    zeroday_keywords = ['0-day', 'zero-day', 'zero day', 'exploit', 'cve-', 'critical', 'vulnerability']

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.get('title', 'Unknown Source')[:20]
            for entry in feed.entries:
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=pytz.utc)
                else:
                    continue
                
                if pub_date > time_limit:
                    title = entry.title
                    summary = entry.get('summary', '')[:400]
                    
                    is_zeroday = any(k in title.lower() or k in summary.lower() for k in zeroday_keywords)
                    
                    articles.append({
                        "source": source_name,
                        "title": title,
                        "link": entry.link,
                        "raw_summary": summary,
                        "summary": "",
                        "date": pub_date.strftime("%Y-%m-%d %H:%M"),
                        "timestamp": pub_date.isoformat(),
                        "is_zeroday": is_zeroday,
                        "processed": False 
                    })
        except Exception as e:
            print(f"Error ({url}): {e}")
    return articles

def summarize_with_gemini(new_articles):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("No API Key found.")
        return new_articles

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    print("Running Gemini AI analysis on new items...")
    for article in new_articles:
        if not article.get('processed'):
            try:
                context = "CRITICAL VULNERABILITY! " if article['is_zeroday'] else ""
                prompt = f"{context}Summarize this cybersecurity news in English in one technical, concise paragraph (Max 35 words). News: {article['title']} - {article['raw_summary']}"
                
                response = model.generate_content(prompt)
                article['summary'] = response.text
                article['processed'] = True 
                time.sleep(12) # SAFE DELAY 12 SECONDS
            except Exception as e:
                print(f"AI Error: {e}")
                article['summary'] = article['raw_summary']
            
    return new_articles

def main():
    existing_articles = load_existing_articles()
    existing_links = {item['link'] for item in existing_articles}

    fresh_articles = fetch_news()
    
    new_unique_articles = [art for art in fresh_articles if art['link'] not in existing_links]
    
    if new_unique_articles:
        print(f"Found {len(new_unique_articles)} new articles.")
        processed_articles = summarize_with_gemini(new_unique_articles)
        all_articles = processed_articles + existing_articles
        all_articles.sort(key=lambda x: x['timestamp'], reverse=True)
        all_articles = all_articles[:500]
        save_articles(all_articles)
    else:
        print("No new articles found.")
        all_articles = existing_articles

    template = Template(HTML_TEMPLATE)
    output_html = template.render(
        items=all_articles,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        github_profile=GITHUB_PROFILE
    )
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(output_html)
    print("index.html created successfully.")

if __name__ == "__main__":
    main()
