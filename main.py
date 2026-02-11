import os
import feedparser
import pytz
from datetime import datetime, timedelta
from jinja2 import Template
import google.generativeai as genai
import time

# --- AYARLAR ---
RSS_FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.cisa.gov/uscert/ncas/alerts.xml",
    "https://krebsonsecurity.com/feed/",
    "https://threatpost.com/feed/"
]

# GitHub Profil Linkin
GITHUB_PROFILE = "https://github.com/merveguler" 

# --- HTML ŞABLONU (AttackRuleMap Style - Icons & English Footer) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cyber Threat Intelligence | Merve Güler</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-color: #0b0c10;
            --card-bg: #1f2833;
            --text-main: #c5c6c7;
            --accent-cyan: #66fcf1;
            --accent-dark: #45a29e;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            flex: 1;
        }

        /* HEADER TASARIMI */
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--accent-dark);
            padding-bottom: 20px;
            margin-bottom: 40px;
        }

        .header-left h1 {
            font-family: 'JetBrains Mono', monospace;
            color: var(--accent-cyan);
            font-size: 1.8rem;
            margin: 0;
            text-shadow: 0 0 10px rgba(102, 252, 241, 0.3);
        }

        /* SAĞ ÜST İKONLAR */
        .header-right {
            display: flex;
            align-items: center;
            gap: 20px; /* İkonlar arası boşluk */
        }

        .icon-link {
            color: var(--text-main);
            font-size: 1.5rem;
            text-decoration: none;
            transition: color 0.3s ease;
        }

        .icon-link:hover {
            color: var(--accent-cyan);
        }

        /* GRID YAPISI */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }

        /* KART TASARIMI */
        .card {
            background-color: var(--card-bg);
            border: 1px solid #2d3842;
            border-radius: 8px;
            padding: 25px;
            transition: transform 0.2s, box-shadow 0.2s;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }

        .card:hover {
            transform: translateY(-5px);
            border-color: var(--accent-cyan);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.5);
        }

        .meta {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: #88929b;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
        }

        .source-tag {
            background: rgba(69, 162, 158, 0.2);
            padding: 2px 6px;
            border-radius: 3px;
            color: var(--accent-cyan);
        }

        h2 {
            font-size: 1.1rem;
            margin: 0 0 15px 0;
            line-height: 1.4;
        }

        h2 a {
            color: #fff;
            text-decoration: none;
            transition: color 0.2s;
        }

        h2 a:hover {
            color: var(--accent-cyan);
        }

        .summary {
            font-size: 0.9rem;
            line-height: 1.6;
            color: #b0b3b8;
            flex-grow: 1;
        }

        /* FOOTER TASARIMI */
        footer {
            text-align: center;
            padding: 30px;
            margin-top: 50px;
            border-top: 1px solid #1f2833;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            color: #666;
        }

        .heart {
            color: #ff69b4; /* Pembe Kalp Rengi */
            font-size: 1.2rem;
            animation: beat 1s infinite alternate;
            display: inline-block;
        }

        @keyframes beat {
            to { transform: scale(1.2); }
        }
    </style>
</head>
<body>

    <div class="container">
        <header>
            <div class="header-left">
                <h1>/// CYBER_INTEL_FEED</h1>
                <small style="color: #666;">Status: ONLINE | Updated: {{ last_updated }}</small>
            </div>
            <div class="header-right">
                <a href="{{ github_profile }}" target="_blank" class="icon-link" title="GitHub Profile">
                    <i class="fab fa-github"></i>
                </a>
                <a href="#" class="icon-link" title="Dark Mode (Active)">
                    <i class="fas fa-moon"></i>
                </a>
            </div>
        </header>

        <div class="grid">
            {% for item in items %}
            <article class="card">
                <div class="meta">
                    <span class="source-tag">{{ item.source }}</span>
                    <span>{{ item.date }}</span>
                </div>
                <h2><a href="{{ item.link }}" target="_blank">{{ item.title }}</a></h2>
                <div class="summary">
                    {{ item.summary | safe }}
                </div>
            </article>
            {% endfor %}
        </div>
    </div>

    <footer>
        Crafted by Merve Güler <span class="heart">🩷</span>
    </footer>

</body>
</html>
"""

def fetch_news():
    articles = []
    utc_now = datetime.now(pytz.utc)
    time_limit = utc_now - timedelta(hours=24)
    print("Haberler taranıyor...")
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
                    articles.append({
                        "source": source_name,
                        "title": entry.title,
                        "link": entry.link,
                        "raw_summary": entry.get('summary', '')[:400],
                        "date": pub_date.strftime("%H:%M"),
                        "timestamp": pub_date
                    })
        except Exception as e:
            print(f"Hata ({url}): {e}")
    return sorted(articles, key=lambda x: x['timestamp'], reverse=True)

def summarize_with_gemini(articles):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("API Key yok, özetleme geçiliyor.")
        return articles

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    print("Gemini AI Analizi yapılıyor...")
    for article in articles:
        try:
            prompt = f"Bu siber güvenlik haberini Türkçe olarak tek bir paragrafta, teknik ve net bir dille özetle. (Max 30 kelime). Haber: {article['title']} - {article['raw_summary']}"
            response = model.generate_content(prompt)
            article['summary'] = response.text
            time.sleep(10) # 10 Saniye Bekleme (Garanti)
        except Exception as e:
            print(f"AI Hatası: {e}")
            article['summary'] = article['raw_summary']
            
    return articles

def main():
    news = fetch_news()
    if news:
        news = summarize_with_gemini(news)
    
    template = Template(HTML_TEMPLATE)
    output_html = template.render(
        items=news,
        last_updated=datetime.now().strftime("%d.%m.%Y %H:%M UTC"),
        github_profile=GITHUB_PROFILE
    )
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(output_html)
    print("index.html başarıyla oluşturuldu.")

if __name__ == "__main__":
    main()
