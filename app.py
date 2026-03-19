import os
import re
import concurrent.futures
import nltk
import feedparser
from flask import Flask, render_template, request
from newspaper import Article, Config

# ==========================================
# 1. 環境設定 (Render/NLTK対策)
# ==========================================
nltk_data_path = os.path.join(os.getcwd(), "nltk_data")
if not os.path.exists(nltk_data_path):
    os.makedirs(nltk_data_path)
nltk.data.path.append(nltk_data_path)

try:
    # newspaper3kの解析に必須のデータをダウンロード
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', download_dir=nltk_data_path)

app = Flask(__name__)

# カテゴリーとGoogleニュースRSSの対応表
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

# ==========================================
# 2. 補助関数 (HTMLタグ削除)
# ==========================================
def remove_html_tags(text):
    if not text: return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

# ==========================================
# 3. 記事解析コアロジック (画像取得強化)
# ==========================================
def fetch_article_content(entry):
    config = Config()
    # 最新ブラウザを装い、AVIF/WebP対応をサイト側に伝える
    config.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    config.request_timeout = 10

    # --- ステップ1: RSSフィード自体から画像を探す ---
    top_image_url = None
    if 'media_content' in entry:
        top_image_url = entry.media_content[0]['url']
    elif 'description' in entry:
        img_match = re.search(r'<img src="(.*?)"', entry.description)
        if img_match:
            top_image_url = img_match.group(1)

    try:
        article = Article(entry.link, config=config)
        article.download()
        article.parse()
        
        # 本文：400文字制限
        content = article.text[:400].replace('\n', '<br>')
        
        # --- ステップ2: メタデータから画像を直接引っこ抜く (AVIF/WebP対策) ---
        # newspaper3kが認識しなくても、HTMLのog:imageタグから直接URLを抽出
        if not top_image_url:
            # 1. meta_img (newspaper3kがメタタグから拾ったもの)
            top_image_url = article.meta_img
            
        if not top_image_url:
            # 2. meta_dataからog:imageを直接指定
            top_image_url = article.meta_data.get('og', {}).get('image')

        if not top_image_url:
            # 3. 最終手段としてライブラリの自動判定
            top_image_url = article.top_image

        # ゴミ取り
        if content.startswith('GE'):
            content = content.replace('GE', '', 1).lstrip()

        if not content or len(content) < 30:
            content = remove_html_tags(getattr(entry, 'summary', ''))
        
        return {
            'title': entry.title, 
            'link': entry.link, 
            'published': getattr(entry, 'published', ''), 
            'content': content,
            'top_image_url': top_image_url
        }
    except Exception as e:
        # 失敗時はRSSの画像だけでも保持して返す
        return {
            'title': entry.title, 
            'link': entry.link, 
            'published': getattr(entry, 'published', ''), 
            'content': remove_html_tags(getattr(entry, 'summary', '')),
            'top_image_url': top_image_url
        }

# ==========================================
# 4. ルート設定 (表示処理)
# ==========================================
@app.route('/')
def index():
    cat_key = request.args.get('cat', 'top')
    rss_url = CATEGORIES.get(cat_key, CATEGORIES['top'])
    
    feed = feedparser.parse(rss_url)
    raw_entries = feed.entries[:6]
    
    # 並列処理で高速化
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        entries = list(executor.map(fetch_article_content, raw_entries))
        
    return render_template('index.html', entries=entries, current_cat=cat_key)

# ==========================================
# 5. 起動設定 (Render/Local)
# ==========================================
if __name__ == '__main__':
    # 外部接続を許可 (0.0.0.0) し、ポート5000で待機
    app.run(debug=True, host='0.0.0.0', port=5000)
