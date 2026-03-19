import os
from flask import Flask, render_template, request
import feedparser
from newspaper import Article, Config
import concurrent.futures
import re
import nltk

# --- NLTKデータの保存先を明示（Render対策） ---
nltk_data_path = os.path.join(os.getcwd(), "nltk_data")
if not os.path.exists(nltk_data_path):
    os.makedirs(nltk_data_path)
nltk.data.path.append(nltk_data_path)

try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', download_dir=nltk_data_path)

app = Flask(__name__)

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
    if not text: return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def fetch_article_content(entry):
    config = Config()
    config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    config.request_timeout = 5

    try:
        article = Article(entry.link, config=config)
        article.download()
        article.parse()
        content = article.text[:800].replace('\n', '<br>')
        
        # ゴミ取り
        if content.startswith('GE'):
            content = content.replace('GE', '', 1).lstrip()

        if not content or len(content) < 30:
            content = remove_html_tags(getattr(entry, 'summary', ''))
        
        return {
            'title': entry.title, 
            'link': entry.link, 
            'published': getattr(entry, 'published', ''), 
            'content': content
        }
    except:
        return {
            'title': entry.title, 
            'link': entry.link, 
            'published': getattr(entry, 'published', ''), 
            'content': remove_html_tags(getattr(entry, 'summary', ''))
        }

@app.route('/')
def index():
    cat_key = request.args.get('cat', 'top')
    rss_url = CATEGORIES.get(cat_key, CATEGORIES['top'])
    
    feed = feedparser.parse(rss_url)
    raw_entries = feed.entries[:6]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        entries = list(executor.map(fetch_article_content, raw_entries))
        
    return render_template('index.html', entries=entries, current_cat=cat_key)

if __name__ == '__main__':
    # Renderではポート5000（または環境変数）でOK
    app.run(debug=True, host='0.0.0.0', port=5000)
