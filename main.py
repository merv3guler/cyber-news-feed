import os
import json
import time
import re
import pytz
from datetime import datetime, timedelta
from jinja2 import Template
import feedparser
import google.generativeai as genai

# --- 1. CONFIGURATION ---
GITHUB_PROFILE = "https://github.com/merv3guler"
DATA_FILE = "data/articles.json"
MAX_HISTORY = 500  # Keep last 500 articles to prevent large file size

RSS_FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.theregister.com/security/headlines.atom",
    "https://www.cisa.gov/uscert/ncas/alerts.xml",
    "https://isc.sans.edu/rssfeed_full.xml",
    "https://krebsonsecurity.com/feed/",
    "https://www.schneier.com/feed/atom/",
    "https://googleprojectzero.blogspot.com/feeds/posts/default",
    "https://blog.trendmicro.com/category/trendlabs-security-intelligence/feed/",
    "https://www.darkreading.com/rss.xml",
    "https://threatpost.com/feed/"
]

# Keywords to map sources to categories
CATEGORY_MAP = {
    "News": ["Hacker News", "Bleeping", "Register", "Dark Reading", "Threatpost"],
    "Alerts": ["CISA", "SANS", "CERT", "Advisory"],
    "Research": ["Krebs", "Schneier", "Google", "Trend Micro", "Project Zero"]
}

# --- 2. HTML TEMPLATE (Frontend) ---
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
            /* DARK MODE VARIABLES */
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --text-main: #c9d1d9;
            --text-muted: #8b949e;
            --border: #30363d;
            --accent: #00ff41;
            --accent-glow: rgba(0, 255, 65, 0.2);
            --danger: #ff003c;
            --sun-color: #f39c12;
            
            /* Category Colors */
            --cat-news: #3498db;
            --cat-alerts: #e67e22;
            --cat-research: #9b59b6;
            --cat-vulns: #e74c3c;
        }

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

        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }

        /* HEADER */
        header {
            display: flex; justify-content: space-between; align-items: center;
            padding-bottom: 20px; border-bottom: 1px solid var(--border); margin-bottom: 20px;
        }
        h1 {
            font-family: 'JetBrains Mono', monospace; color: var(--accent); margin: 0;
            font-size: 1.8rem; text-shadow: 0 0 5px var(--accent-glow);
        }
        .header-controls { display: flex; gap: 15px; align-items: center; }
        .icon-btn {
            background: none; border: 1px solid var(--border); color: var(--text-main);
            padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 1.1rem; transition: all 0.2s;
        }
        .icon-btn:hover { border-color: var(--accent); color: var(--accent); }
        .fa-sun { color: var(--sun-color); filter: drop-shadow(0 0 3px var(--sun-color)); }

        /* FILTERS */
        .controls-bar { display: flex; flex-direction: column; gap: 15px; margin-bottom: 30px; }
        .filter-group { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
        .filter-label { font-size: 0.8rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }
        
        .filter-btn {
            background-color: var(--card-bg); border: 1px solid var(--border); color: var(--text-muted);
            padding: 6px 12px; border-radius: 20px; cursor: pointer; font-size: 0.85rem; font-weight: 600; transition: 0.2s;
        }
        .filter-btn:hover, .filter-btn.active { background-color: var(--accent); color: #000; border-color: var(--accent); }
        .filter-btn.zeroday-btn { border-color: var(--danger); color: var(--danger); }
        .filter-btn.zeroday-btn:hover, .filter-btn.zeroday-btn.active { background-color: var(--danger); color: #fff; }

        /* GRID */
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
        
        .card {
            background-color: var(--card-bg); border: 1px solid var(--border); border-radius: 8px;
            padding: 20px; display: flex; flex-direction: column; position: relative;
            transition: transform 0.2s; overflow: hidden; border-top: 3px solid transparent;
        }
        .card:hover { transform: translateY(-3px); box-shadow: 0 5px 15px rgba(0,0,0,0.3); border-color: var(--accent); }
        
        /* Category Borders */
        .card[data-category="News"] { border-top-color: var(--cat-news); }
        .card[data-category="Alerts"] { border-top-color: var(--cat-alerts); }
        .card[data-category="Research"] { border-top-color: var(--cat-research); }
        .card[data-category="Vulns"] { border-top-color: var(--cat-vulns); }

        .zeroday-banner {
            background-color: var(--danger); color: #fff; font-size: 0.7rem; font-weight: bold;
            padding: 4px 8px; position: absolute; top: 0; right: 0;
            border-bottom-left-radius: 8px; animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }

        .meta { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.75rem; font-family: 'JetBrains Mono'; }
        .category-badge { font-weight: bold; text-transform: uppercase; }
        
        h2 { font-size: 1.1rem; margin: 0 0 10px 0; line-height: 1.4; }
        h2 a { color: var(--text-main); text-decoration: none; }
        h2 a:hover { color: var(--accent); }
        
        .summary { font-size: 0.9rem; line-height: 1.5; color: var(--text-muted); margin-bottom: 20px; flex-grow: 1; }

        .card-footer {
            border-top: 1px solid var(--border); padding-top: 15px;
            display: flex; justify-content: space-between; align-items: center;
        }
        .share-links { display: flex; gap: 15px; }
        .share-icon { color: var(--text-muted); font-size: 1.1rem; transition: 0.2s; }
        .share-icon:hover { color: var(--accent); transform: scale(1.1); }
        
        footer { margin-top: 50px; text-align: center; color: var(--text-muted); font-size: 0.85rem; padding-bottom: 20px; }
        .heart { color: #ff003c; animation: beat 1s infinite alternate; display: inline-block; }
        @keyframes beat { to { transform: scale(1.1); } }
        
        .export-btn {
            background-color: var(--card-bg); border: 1px solid var(--accent); color: var(--accent);
            padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: bold;
        }
        .export-btn:hover { background-color: var(--accent); color: #000; }
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
            <button class="icon-btn" id="themeToggle"><i class="fas fa-sun"></i></button>
            <a href="{{ github_profile }}" target="_blank" class="icon-btn"><i class="fab fa-github"></i></a>
        </div>
    </header>

    <div class="controls-bar">
        <div class="filter-group">
            <span class="filter-label">CATEGORIES:</span>
            <button class="filter-btn active" onclick="filterNews('all')">ALL</button>
            <button class="filter-btn zeroday-btn" onclick="filterNews('zeroday')">ZERO DAY</button>
            <button class="filter-btn" onclick="filterNews('News')">NEWS</button>
            <button class="filter-btn" onclick="filterNews('Alerts')">ALERTS</button>
            <button class="filter-btn" onclick="filterNews('Research')">RESEARCH</button>
        </div>
        <div style="display:flex; justify-content:space-between; width:100%;">
            <div class="filter-group" id="sourceFilterContainer">
                <span class="filter-label">SOURCES:</span>
                </div>
            <button class="export-btn" onclick="exportToExcel()"><i class="fas fa-file-excel"></i> Export CSV</button>
        </div>
    </div>

    <div class="grid" id="newsGrid">
        {% for item in items %}
        <article class="card" 
                 data-source="{{ item.source }}" 
                 data-category="{{ item.category }}" 
                 data-zeroday="{{ 'true' if item.is_zeroday else 'false' }}">
            
            {% if item.is_zeroday %}<div class="zeroday-banner">⚠️ ZERO-DAY DETECTED</div>{% endif %}
            
            <div class="meta">
                <span class="category-badge" style="color: var(--cat-{{ item.category | lower }})">{{ item.category }}</span>
                <span>{{ item.date }}</span>
            </div>
            <h2><a href="{{ item.link }}" target="_blank">{{ item.title }}</a></h2>
            <div class="summary">{{ item.summary | safe }}</div>

            <div class="card-footer">
                <span style="font-size:0.75rem; color:var(--text-muted)">{{ item.source }}</span>
                <div class="share-links">
                    <a href="https://wa.me/?text={{ item.link }}" target="_blank" class="share-icon"><i class="fab fa-whatsapp"></i></a>
                    <a href="https://www.linkedin.com/sharing/share-offsite/?url={{ item.link }}" target="_blank" class="share-icon"><i class="fab fa-linkedin"></i></a>
                    <a href="https://twitter.com/intent/tweet?text={{ item.title }}&url={{ item.link }}" target="_blank" class="share-icon"><i class="fa-brands fa-x-twitter"></i></a>
                    <a href="mailto:?subject=Cyber Intel&body={{ item.title }} - {{ item.link }}" class="share-icon"><i class="fas fa-envelope"></i></a>
                </div>
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
    // 1. THEME TOGGLE
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

    // 2. SOURCE FILTER GENERATION
    const cards = document.querySelectorAll('.card');
    const sources = new Set();
    cards.forEach(card => sources.add(card.getAttribute('data-source')));
    const sourceContainer = document.getElementById('sourceFilterContainer');
    
    Array.from(sources).sort().forEach(source => {
        const btn = document.createElement('button');
        btn.innerText = source;
        btn.className = 'filter-btn';
        btn.onclick = () => filterNews(source);
        sourceContainer.appendChild(btn);
    });

    // 3. FILTER LOGIC
    function filterNews(criteria) {
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        cards.forEach(card => {
            const source = card.getAttribute('data-source');
            const category = card.getAttribute('data-category');
            const isZeroDay = card.getAttribute('data-zeroday') === 'true';

            let show = false;
            if (criteria === 'all') show = true;
            else if (criteria === 'zeroday') show = isZeroDay;
            else if (category === criteria) show = true;
            else if (source === criteria) show = true;

            card.style.display = show ? 'flex' : 'none';
        });
    }

    // 4. EXCEL EXPORT
    function exportToExcel() {
        let csv = "Category,Source,Date,Title,Link,Summary\\n";
        cards.forEach(card => {
            if (card.style.display !== 'none') {
                const cat = card.getAttribute('data-category');
                const src = card.getAttribute('data-source');
                const date = card.querySelector('.meta span:last-child').innerText;
                const title = card.querySelector('h2 a').innerText.replace(/,/g, '');
                const link = card.querySelector('h2 a').href;
                const sum = card.querySelector('.summary').innerText.replace(/\\n/g, ' ').replace(/,/g, '');
                csv += `${cat},${src},${date},${title},${link},"${sum}"\\n`;
            }
        });
        const link = document.createElement("a");
        link.href = encodeURI("data:text/csv;charset=utf-8," + csv);
        link.download = "cyber_intel_report.csv";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
</script>
</body>
</html>
"""

# --- 3. BACKEND LOGIC ---

def clean_html(raw_html):
    """Remove HTML tags from summaries."""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()

def determine_category(source_name):
    """Map source name to a specific category."""
    for category, keywords in CATEGORY_MAP.items():
        for keyword in keywords:
            if keyword.lower() in source_name.lower():
                return category
    return "News"  # Default category

def load_history():
    """Load existing articles from JSON."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_history(articles):
    """Save articles to JSON."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)

def fetch_rss_feeds():
    """Fetch and parse RSS feeds."""
    articles = []
    utc_now = datetime.now(pytz.utc)
    time_limit = utc_now - timedelta(hours=24)
    
    print("[-] Scanning RSS Feeds...")
    zeroday_keywords = ['0-day', 'zero-day', 'zero day', 'exploit', 'cve-', 'critical', 'vulnerability']

    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            # Safe get for source title
            source_name = feed.feed.get('title', 'Unknown Source')[:20]
            category = determine_category(source_name)

            for entry in feed.entries:
                # Parse date
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=pytz.utc)
                else:
                    continue
                
                # Filter by last 24h
                if pub_date > time_limit:
                    title = entry.title
                    # Get summary and clean HTML
                    raw_summary = entry.get('summary', entry.get('description', ''))
                    clean_summary = clean_html(raw_summary)[:500]
                    
                    is_zeroday = any(k in title.lower() or k in clean_summary.lower() for k in zeroday_keywords)
                    
                    articles.append({
                        "source": source_name,
                        "category": category,
                        "title": title,
                        "link": entry.link,
                        "raw_summary": clean_summary,
                        "summary": "", # To be filled by AI
                        "date": pub_date.strftime("%Y-%m-%d %H:%M"),
                        "timestamp": pub_date.isoformat(),
                        "is_zeroday": is_zeroday,
                        "processed": False
                    })
        except Exception as e:
            print(f"[!] Error processing {url}: {e}")
            
    return articles

def process_ai_summaries(new_articles):
    """Summarize new articles using Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[!] No GEMINI_API_KEY found. Skipping AI.")
        return new_articles

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    count = 0
    total = len(new_articles)
    print(f"[-] Processing {total} new articles with AI...")

    for article in new_articles:
        if not article.get('processed'):
            count += 1
            try:
                print(f"    [{count}/{total}] Summarizing: {article['title'][:30]}...")
                context = "CRITICAL VULNERABILITY! " if article['is_zeroday'] else ""
                prompt = (f"{context}Summarize this cybersecurity news in English in one technical, "
                          f"concise paragraph (Max 35 words). News: {article['title']} - {article['raw_summary']}")
                
                response = model.generate_content(prompt)
                article['summary'] = response.text
                article['processed'] = True
                
                # --- SAFETY DELAY: 20 SECONDS ---
                time.sleep(20) 
                
            except Exception as e:
                print(f"    [!] AI Error: {e}")
                article['summary'] = article['raw_summary'] # Fallback
            
    return new_articles

def main():
    # 1. Load History
    history = load_history()
    history_links = {item['link'] for item in history}

    # 2. Fetch Fresh News
    fresh_news = fetch_rss_feeds()
    
    # 3. Filter Duplicates
    new_unique_news = [item for item in fresh_news if item['link'] not in history_links]
    
    if new_unique_news:
        print(f"[*] Found {len(new_unique_news)} new unique articles.")
        
        # 4. AI Processing
        processed_news = process_ai_summaries(new_unique_news)
        
        # 5. Merge and Sort
        full_list = processed_news + history
        full_list.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # 6. Trim History
        full_list = full_list[:MAX_HISTORY]
        
        # 7. Save Data
        save_history(full_list)
        print("[*] Database updated.")
    else:
        print("[*] No new articles found. Generating page from history.")
        full_list = history

    # 8. Generate HTML
    template = Template(HTML_TEMPLATE)
    output_html = template.render(
        items=full_list,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        github_profile=GITHUB_PROFILE
    )
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(output_html)
    
    print("[+] index.html generated successfully.")

if __name__ == "__main__":
    main()
