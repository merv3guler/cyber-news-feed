import os
import feedparser
import pytz
from datetime import datetime, timedelta
from jinja2 import Template
from openai import OpenAI

# --- AYARLAR ---
RSS_FEEDS = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://www.bleepingcomputer.com/feed/",
    "https://www.cisa.gov/uscert/ncas/alerts.xml"
]

# --- HTML ŞABLONU (Cyberpunk Tema) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cyber Threat Intel</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: 'Courier New', monospace; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #00ff41; text-shadow: 0 0 5px #00ff41; border-bottom: 1px solid #30363d; padding-bottom: 10px; }
        .card { background: #161b22; border: 1px solid #30363d; margin-bottom: 20px; padding: 15px; border-radius: 6px; }
        .card:hover { border-color: #00ff41; }
        .meta { color: #8b949e; font-size: 0.8em; margin-bottom: 10px; display: block; }
        .badge { background: #238636; color: white; padding: 2px 5px; border-radius: 4px; font-size: 0.7em; }
        a { color: #58a6ff; text-decoration: none; font-weight: bold; font-size: 1.1em; }
        .summary { margin-top: 10px; line-height: 1.5; color: #e6edf3; }
        .footer { text-align: center; margin-top: 40px; color: #484f58; font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>/// DAILY_THREAT_INTEL_FEED</h1>
        <p style="color: #8b949e;">LAST_UPDATE: {{ last_updated }} | SYSTEM: ONLINE</p>
        
        {% for item in items %}
        <div class="card">
            <span class="meta"><span class="badge">{{ item.source }}</span> {{ item.date }}</span>
            <a href="{{ item.link }}" target="_blank">> {{ item.title }}</a>
            <div class="summary">
                {{ item.summary | safe }}
            </div>
        </div>
        {% endfor %}
        
        <div class="footer">Generated automatically via GitHub Actions</div>
    </div>
</body>
</html>
"""

def fetch_news():
    articles = []
    # UTC Zamanı
    utc_now = datetime.now(pytz.utc)
    # Son 24 saat
    time_limit = utc_now - timedelta(hours=24)
    
    print("Fetching news...")
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.get('title', 'Unknown Source')
            
            for entry in feed.entries:
                # Tarih parsing işlemi
                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=pytz.utc)
                else:
                    continue
                    
                if pub_date > time_limit:
                    articles.append({
                        "source": source_name,
                        "title": entry.title,
                        "link": entry.link,
                        "raw_summary": entry.get('summary', '')[:500],
                        "date": pub_date.strftime("%Y-%m-%d %H:%M"),
                        "timestamp": pub_date
                    })
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            
    # Yeniden eskiye sırala
    return sorted(articles, key=lambda x: x['timestamp'], reverse=True)

def summarize_with_ai(articles):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("No API Key found. Skipping AI summary.")
        return articles

    client = OpenAI(api_key=api_key)
    
    for article in articles:
        try:
            prompt = f"Summarize this security news for a technical report in Turkish (2 sentences max). News: {article['title']} - {article['raw_summary']}"
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150
            )
            article['summary'] = response.choices[0].message.content
        except Exception as e:
            print(f"AI Error: {e}")
            article['summary'] = article['raw_summary']
            
    return articles

def main():
    # 1. Veri Çek
    news = fetch_news()
    
    # 2. AI ile Özetle (Varsa)
    if news:
        news = summarize_with_ai(news)
    
    # 3. HTML Oluştur
    template = Template(HTML_TEMPLATE)
    output_html = template.render(
        items=news,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    )
    
    # 4. Dosyayı Yaz (GitHub Pages için index.html)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(output_html)
    
    print("index.html created successfully.")

if __name__ == "__main__":
    main()
