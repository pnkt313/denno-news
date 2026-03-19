import os
import re
import concurrent.futures
import feedparser
from flask import Flask, render_template, request
from newspaper import Article, Config

app = Flask(__name__)

CATEGORIES = {
    'top': 'https://news.google.com/news/rss?hl=ja&gl=JP&ceid=JP:ja',
    'japan': 'https://news.google.com/news/rss/headlines/section/topic/NATION?hl=ja&gl=JP&ceid=JP:ja',
    'world': 'https://news.google.com/news/rss/headlines/section/topic/WORLD?hl=ja&gl=JP&ceid=JP:ja',
    'business': 'https://news.google.com/news/rss/headlines/section/topic/BUSINESS?hl=ja&gl=JP&ceid=JP:ja',
    'technology': 'https://news.google.com/news/rss/headlines/section/topic/TECHNOLOGY?hl=ja&gl=JP&ceid=JP:ja',
    'entertainment': 'https://news.google.com/news/rss/headlines/section/topic/ENTERTAINMENT?hl=ja&gl=JP&ceid=JP:ja',
    'sports': 'https://news.google.com/news/rss/headlines/section/topic/SPORTS?hl=ja&gl=JP&ceid=JP:ja',
    'science': 'https://news.google.com/news/rss/headlines/section/topic/SCIENCE?hl=ja&gl=JP&ceid=JP:ja',
    'yahoo_main': 'https://news.yahoo.co.jp/rss/topics/top-picks.xml',
    'yahoo_biz': 'https://news.yahoo.co.jp/rss/topics/business.xml'
}

def remove_html_tags(text):
    if not text: return ""
    return re.sub(r'<.*?>', '', text)

def fetch_article_content(entry):
    config = Config()
    config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    # タイムアウトを3秒に。Renderの30秒制限に余裕を持たせます
    config.request_timeout = 3 
    config.fetch_images = False

    rss_summary = remove_html_tags(entry.get('summary', ''))

    try:
        article = Article(entry.link, config=config)
        article.download()
        article.parse()
        
        content = article.text[:400].replace('\n', '<br>')
        if not content or len(content) < 20:
            content = rss_summary
    except Exception as e:
        # エラー時はログに出力（Renderのログで見れます）
        print(f"Error fetching {entry.link}: {e}")
        content = rss_summary if rss_summary else "本文を取得できませんでした。"
        
    return {
        'title': entry.title, 
        'link': entry.link, 
        'published': getattr(entry, 'published', ''), 
        'content': content
    }

@app.route('/')
def index():
    cat_key = request.args.get('cat', 'top')
    rss_url = CATEGORIES.get(cat_key, CATEGORIES['top'])
    
    feed = feedparser.parse(rss_url)
    # 最初は確認のため4記事に絞る
    raw_entries = feed.entries[:4]
    
    # Renderの負荷を考え、並列数を2に下げる
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        entries = list(executor.map(fetch_article_content, raw_entries))
        
    return render_template('index.html', entries=entries, current_cat=cat_key)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
