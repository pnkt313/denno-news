from flask import Flask, render_template, request
import feedparser
from newspaper import Article, Config  # ← Configをしっかりインポート
import concurrent.futures
import re
import nltk

# NLTKデータの準備
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')

app = Flask(__name__)

# カテゴリーとRSS URLの対応表
CATEGORIES = {
    'top': 'https://news.google.com/news/rss?hl=ja&gl=JP&ceid=JP:ja',
    'japan': 'https://news.google.com/news/rss/headlines/section/topic/NATION?hl=ja&gl=JP&ceid=JP:ja',
    'world': 'https://news.google.com/news/rss/headlines/section/topic/WORLD?hl=ja&gl=JP&ceid=JP:ja',
    'business': 'https://news.google.com/news/rss/headlines/section/topic/BUSINESS?hl=ja&gl=JP&ceid=JP:ja',
    'technology': 'https://news.google.com/news/rss/headlines/section/topic/TECHNOLOGY?hl=ja&gl=JP&ceid=JP:ja',
    'entertainment': 'https://news.google.com/news/rss/headlines/section/topic/ENTERTAINMENT?hl=ja&gl=JP&ceid=JP:ja',
    'sports': 'https://news.google.com/news/rss/headlines/section/topic/SPORTS?hl=ja&gl=JP&ceid=JP:ja',
    'science': 'https://news.google.com/news/rss/headlines/section/topic/SCIENCE?hl=ja&gl=JP&ceid=JP:ja'
}

def remove_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

# app.py の fetch_article_content をシンプルに
def fetch_article_content(entry):
    config = Config()
    config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0...)" # 略
    config.request_timeout = 8

    try:
        article = Article(entry.link, config=config)
        article.download()
        article.parse()
        content = article.text[:800].replace('\n', '<br>')
        # 「GE」などのゴミ取り
        content = content.lstrip().removeprefix('GE').replace('GE', '')

        if not content or len(content) < 30:
            content = remove_html_tags(entry.summary)
        
        return {
            'title': entry.title, 
            'link': entry.link, 
            'published': entry.published, 
            'content': content
        }
    except:
        return {
            'title': entry.title, 
            'link': entry.link, 
            'published': entry.published, 
            'content': remove_html_tags(entry.summary)
        }

@app.route('/')
def index():
    cat_key = request.args.get('cat', 'top')
    rss_url = CATEGORIES.get(cat_key, CATEGORIES['top'])
    
    feed = feedparser.parse(rss_url)
    raw_entries = feed.entries[:15]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        entries = list(executor.map(fetch_article_content, raw_entries))
        
    return render_template('index.html', entries=entries, current_cat=cat_key)

if __name__ == '__main__':
    app.run(debug=True, port=5000)