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
GITHUB_REPO = "https://github.com/merv3guler/cyber-news-feed"
DATA_FILE = "data/articles.json"
MAX_HISTORY = 600

# GÜNCELLENMİŞ DEV KAYNAK LİSTESİ
RSS_FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.cisa.gov/uscert/ncas/alerts.xml",
    "https://feeds.feedburner.com/GoogleOnlineSecurityBlog",
    "https://www.theregister.com/security/headlines.atom",
    "https://isc.sans.edu/rssfeed_full.xml",
    "https://krebsonsecurity.com/feed/",
    "https://www.schneier.com/feed/atom/",
    "https://unit42.paloaltonetworks.com/feed/",
    "https://blog.trendmicro.com/category/trendlabs-security-intelligence/feed/",
    "https://www.darkreading.com/rss.xml",
    "https://threatpost.com/feed/",
    "https://www.exploit-db.com/rss.xml"
]

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
            --source-badge-bg: #1f6feb;
        }

        body.light-mode {
            --bg-color: #f6f8fa;
            --card-bg: #ffffff;
            --text-main: #24292f;
            --text-muted: #57606a;
            --border: #d0d7de;
            --accent: #1f883d;
            --accent-glow: rgba(31, 136, 61, 0.1);
            --source-badge-bg: #0969da;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            transition: background-color 0.3s, color 0.3s;
            display: flex; flex-direction: column; min-height: 100vh;
        }

        .container { max-width: 1000px; margin: 0 auto; padding: 20px; flex: 1; width: 100%; }

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
            text-decoration: none; display: flex; align-items: center; justify-content: center;
        }
        .icon-btn:hover { border-color: var(--accent); color: var(--accent); }
        .fa-sun { color: var(--sun-color); filter: drop-shadow(0 0 3px var(--sun-color)); }

        /* FILTERS */
        .controls-bar { display: flex; flex-direction: column; gap: 15px; margin-bottom: 30px; }
        
        .filter-container {
            display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
        }

        .filter-label { font-size: 0.8rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; font-weight: bold; margin-right: 5px; }
        
        .filter-btn {
            background-color: var(--card-bg); border: 1px solid var(--border); color: var(--text-muted);
            padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 600; transition: 0.2s;
        }
        .filter-btn:hover, .filter-btn.active { background-color: var(--accent); color: #000; border-color: var(--accent); }
        .filter-btn.zeroday-btn { border-color: var(--danger); color: var(--danger); }
        .filter-btn.zeroday-btn:hover, .filter-btn.zeroday-btn.active { background-color: var(--danger); color: #fff; }

        /* LIST LAYOUT */
        .grid { display: flex; flex-direction: column; gap: 20px; }
        
        .card {
            background-color: var(--card-bg); border: 1px solid var(--border); border-radius: 6px;
            padding: 20px; display: flex; flex-direction: column; position: relative;
            transition: transform 0.2s; overflow: hidden; border-left: 4px solid var(--accent);
        }
        .card:hover { transform: translateX(5px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); border-color: var(--accent); }
        
        .zeroday-banner {
            background-color: var(--danger); color: #fff; font-size: 0.7rem; font-weight: bold;
            padding: 4px 8px; position: absolute; top: 0; right: 0;
            border-bottom-left-radius: 6px; animation: pulse 1.5s infinite;
        }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }

        .meta { display: flex; gap: 15px; margin-bottom: 8px; font-size: 0.75rem; font-family: 'JetBrains Mono'; align-items: center;}
        
        .source-badge { 
            font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;
            color: var(--source-badge-bg);
        }
        .date-badge { color: var(--text-muted); }
        
        h2 { font-size: 1.2rem; margin: 0 0 10px 0; line-height: 1.3; }
        h2 a { color: var(--text-main); text-decoration: none; }
        h2 a:hover { color: var(--accent); text-decoration: underline; }
        
        .summary { font-size: 0.95rem; line-height: 1.6; color: var(--text-muted); margin-bottom: 15px; }

        .card-footer {
            border-top: 1px solid var(--border); padding-top: 12px;
            display: flex; justify-content: flex-end; align-items: center;
        }
        .share-links { display: flex; gap: 15px; }
        .share-icon { color: var(--text-muted); font-size: 1.1rem; transition: 0.2s; }
        .share-icon:hover { color: var(--accent); transform: scale(1.1); }
        .share-icon:hover .fa-x-twitter { color: var(--text-main); }
        
        /* PAGINATION */
        .pagination { display: flex; justify-content: center; gap: 10px; margin-top: 40px; }
        .page-btn {
            background: var(--card-bg); border: 1px solid var(--border); color: var(--text-main);
            padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: bold;
        }
        .page-btn:hover { border-color: var(--accent); color: var(--accent); }
        .page-btn:disabled { opacity: 0.5; cursor: not-allowed; border-color: var(--border); color: var(--text-muted); }
        .page-info { align-self: center; font-family: 'JetBrains Mono'; font-size: 0.9rem; }

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
                Status: <span style="color:var(--accent)">ONLINE</span> | {{ last_updated }}
            </small>
        </div>
        <div class="header-controls">
            <button class="icon-btn" id="themeToggle"><i class="fas fa-sun"></i></button>
            <a href="{{ github_repo }}" target="_blank" class="icon-btn" title="Go to Repo"><i class="fab fa-github"></i></a>
        </div>
    </header>

    <div class="controls-bar">
        <div class="filter-container">
            <span class="filter-label">FILTERS:</span>
            <button class="filter-btn active" onclick="applyFilter('all')">ALL</button>
            <button class="filter-btn zeroday-btn" onclick="applyFilter('zeroday')">ZERO DAY</button>
            
            <div id="dynamicSourceFilters" style="display:contents;"></div>
        </div>
        
        <div style="display:flex; justify-content:flex-end; margin-top:10px;">
            <button class="export-btn" onclick="exportToExcel()"><i class="fas fa-file-excel"></i> Export CSV</button>
        </div>
    </div>

    <div class="grid" id="newsGrid">
        {% for item in items %}
        <article class="card" 
                 data-source="{{ item.source }}" 
                 data-zeroday="{{ 'true' if item.is_zeroday else 'false' }}">
            
            {% if item.is_zeroday %}<div class="zeroday-banner">⚠️ ZERO-DAY DETECTED</div>{% endif %}
            
            <div class="meta">
                <span class="source-badge">{{ item.source }}</span>
                <span class="date-badge"> | {{ item.date }}</span>
            </div>
            <h2><a href="{{ item.link }}" target="_blank">{{ item.title }}</a></h2>
            <div class="summary">{{ item.summary | safe }}</div>

            <div class="card-footer">
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

    <div class="pagination" id="paginationControls">
        <button class="page-btn" onclick="changePage(-1)" id="prevBtn">< Previous</button>
        <span class="page-info" id="pageInfo">Page 1</span>
        <button class="page-btn" onclick="changePage(1)" id="nextBtn">Next ></button>
    </div>

    <footer>
        Developed by <a href="{{ github_repo }}" style="color:var(--text-main);text-decoration:none;font-weight:bold;">Merve Guler</a> 
        <span class="heart">🩷</span>
    </footer>
</div>

<script>
    // --- VARIABLES ---
    const cards = Array.from(document.querySelectorAll('.card'));
    const itemsPerPage = 9; 
    let currentPage = 1;
    let filteredCards = cards; 

    // --- 1. THEME TOGGLE ---
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

    // --- 2. SOURCE FILTER GENERATION ---
    const sources = new Set();
    cards.forEach(card => sources.add(card.getAttribute('data-source')));
    const sourceContainer = document.getElementById('dynamicSourceFilters');
    
    Array.from(sources).sort().forEach(source => {
        const btn = document.createElement('button');
        btn.innerText = source;
        btn.className = 'filter-btn';
        btn.onclick = () => applyFilter(source);
        sourceContainer.appendChild(btn);
    });

    // --- 3. FILTER LOGIC ---
    function applyFilter(criteria) {
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        filteredCards = cards.filter(card => {
            const source = card.getAttribute('data-source');
            const isZeroDay = card.getAttribute('data-zeroday') === 'true';

            if (criteria === 'all') return true;
            if (criteria === 'zeroday') return isZeroDay;
            if (source === criteria) return true;
            return false;
        });

        currentPage = 1;
        renderPagination();
    }

    // --- 4. PAGINATION LOGIC ---
    function renderPagination() {
        const totalPages = Math.ceil(filteredCards.length / itemsPerPage);
        
        cards.forEach(card => card.style.display = 'none');

        const start = (currentPage - 1) * itemsPerPage;
        const end = start + itemsPerPage;
        const pageItems = filteredCards.slice(start, end);

        pageItems.forEach(card => card.style.display = 'flex');

        document.getElementById('pageInfo').innerText = `Page ${currentPage} of ${totalPages || 1}`;
        document.getElementById('prevBtn').disabled = currentPage === 1;
        document.getElementById('nextBtn').disabled = currentPage >= totalPages;
        
        document.getElementById('paginationControls').style.display = filteredCards.length > 0 ? 'flex' : 'none';
    }

    function changePage(direction) {
        currentPage += direction;
        renderPagination();
        window.scrollTo(0, 0); 
    }

    // --- 5. EXCEL EXPORT ---
    function exportToExcel() {
        let csv = "Source,Date,Title,Link,Summary\\n";
        filteredCards.forEach(card => {
            const src = card.getAttribute('data-source');
            const date = card.querySelector('.meta span:last-child').innerText.replace('| ', '');
            const title = card.querySelector('h2 a').innerText.replace(/,/g, '');
            const link = card.querySelector('h2 a').href;
            const sum = card.querySelector('.summary').innerText.replace(/\\n/g, ' ').replace(/,/g, '');
            csv += `${src},${date},${title},${link},"${sum}"\\n`;
        });
        const link = document.createElement("a");
        link.href = encodeURI("data:text/csv;charset=utf-8," + csv);
        link.download = "cyber_intel_report.csv";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    renderPagination();

</script>
</body>
</html>
"""

# --- 3. BACKEND LOGIC ---

def clean_html(raw_html):
    """Remove HTML tags and cut cleanly."""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    # Cut at 400 chars but try to keep word boundary
    if len(cleantext) > 400:
        return cleantext[:400].rsplit(' ', 1)[0] + "..."
    return cleantext.strip()

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
                    clean_summary = clean_html(raw_summary)
                    
                    is_zeroday = any(k in title.lower() or k in clean_summary.lower() for k in zeroday_keywords)
                    
                    articles.append({
                        "source": source_name,
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
                # Explicitly ask for full sentences
                prompt = (f"{context}Summarize this cybersecurity news in English. "
                          f"Provide exactly one complete, technical paragraph. Do not cut off sentences. "
                          f"Max 50 words. News: {article['title']} - {article['raw_summary']}")
                
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
        
        # 6. Trim History (Keep last 600)
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
        github_repo=GITHUB_REPO
    )
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(output_html)
    
    print("[+] index.html generated successfully.")

if __name__ == "__main__":
    main()
