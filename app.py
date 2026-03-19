import os
import re
import concurrent.futures
import nltk
import feedparser
from flask import Flask, render_template, request
from newspaper import Article, Config

# --- 環境設定 ---
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
    top_image_url = None
    
    # --- 【重要】RSSの全フィールドから画像URLを力技で探す ---
    # 探す対象：summary, description, media_content
    search_text = entry.get('summary', '') + entry.get('description', '')
    
    # 1. media_contentタグをチェック
    if 'media_content' in entry:
        top_image_url = entry.media_content[0]['url']
    
    # 2. summaryやdescriptionの中の<img>タグを正規表現で探す
    if not top_image_url:
        img_match = re.search(r'src="([^"]+)"', search_text)
        if img_match:
            top_image_url = img_match.group(1)

    config = Config()
    config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    config.request_timeout = 5 # 読み込みを速くするために短縮

    try:
        # 記事本文の取得（文字数400制限）
        article = Article(entry.link, config=config)
        article.download()
        article.parse()
        content = article.text[:400].replace('\n', '<br>')

        # それでも画像がなければ解析結果から
        if not top_image_url:
            top_image_url = article.top_image

        if not content or len(content) < 30:
            content = remove_html_tags(search_text)
        
        return {
            'title': entry.title, 
            'link': entry.link, 
            'published': getattr(entry, 'published', ''), 
            'content': content,
            'top_image_url': top_image_url
        }
    except:
        return {
            'title': entry.title, 
            'link': entry.link, 
            'published': getattr(entry, 'published', ''), 
            'content': remove_html_tags(search_text),
            'top_image_url': top_image_url
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
    app.run(debug=True, host='0.0.0.0', port=5000)
