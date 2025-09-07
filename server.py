from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import feedparser
import json
import time
import os
from datetime import datetime, timedelta
import re
from urllib.parse import urljoin, urlparse
import threading
import logging

app = Flask(__name__)
CORS(app)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache das notícias
news_cache = {
    'articles': [],
    'last_update': None,
    'by_category': {}
}

# Configuração da NewsAPI
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')
NEWSAPI_BASE_URL = 'https://newsapi.org/v2'

# Configuração dos sites de notícias brasileiros
NEWS_SOURCES = {
    'g1': {
        'rss_url': 'https://g1.globo.com/rss/g1/',
        'base_url': 'https://g1.globo.com',
        'name': 'G1'
    },
    'uol': {
        'rss_url': 'https://rss.uol.com.br/feed/noticias.xml',
        'base_url': 'https://www.uol.com.br',
        'name': 'UOL Notícias'
    },
    'folha': {
        'rss_url': 'https://www1.folha.uol.com.br/rss/geral.xml',
        'base_url': 'https://www1.folha.uol.com.br',
        'name': 'Folha de S.Paulo'
    },
    'estadao': {
        'rss_url': 'https://estadao.com.br/rss/geral.xml',
        'base_url': 'https://estadao.com.br',
        'name': 'O Estado de S. Paulo'
    },
    'cnn_brasil': {
        'rss_url': 'https://www.cnnbrasil.com.br/feed/',
        'base_url': 'https://www.cnnbrasil.com.br',
        'name': 'CNN Brasil'
    }
}

# Categories mapping
CATEGORY_MAPPING = {
    'technology': ['tecnologia', 'tech', 'inovação', 'digital'],
    'sports': ['esportes', 'futebol', 'olimpiadas', 'copa'],
    'business': ['economia', 'mercado', 'empresas', 'financas'],
    'entertainment': ['entretenimento', 'famosos', 'cultura', 'tv'],
    'general': ['geral', 'brasil', 'mundo', 'politica']
}

def get_headers():
    """Headers para simular um navegador real"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

def clean_text(text):
    """Limpa e formata o texto"""
    if not text:
        return ""
    
    # Remove tags HTML
    text = BeautifulSoup(text, 'html.parser').get_text()
    
    # Remove espaços extras e quebras de linha
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove caracteres especiais problemáticos
    text = text.replace('\xa0', ' ').replace('\u200b', '')
    
    return text

def extract_article_content(url, source_name):
    """Extrai o conteúdo completo de um artigo"""
    try:
        response = requests.get(url, headers=get_headers(), timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Selectors específicos para cada site
        selectors = {
            'G1': [
                '.content-text__container p',
                '.mc-article-body p',
                'article p'
            ],
            'UOL Notícias': [
                '.text p',
                '.content-text p',
                'article p'
            ],
            'Folha de S.Paulo': [
                '.c-news__body p',
                'article p',
                '.content p'
            ],
            'O Estado de S. Paulo': [
                '.content p',
                'article p',
                '.news-content p'
            ],
            'CNN Brasil': [
                '.single-content p',
                'article p',
                '.post-content p'
            ]
        }
        
        content_paragraphs = []
        
        # Tenta selectors específicos primeiro
        if source_name in selectors:
            for selector in selectors[source_name]:
                paragraphs = soup.select(selector)
                if paragraphs:
                    content_paragraphs = paragraphs
                    break
        
        # Fallback para selectors genéricos
        if not content_paragraphs:
            generic_selectors = [
                'article p',
                '.content p',
                '.post-content p',
                '.article-content p',
                '.news-content p',
                'main p'
            ]
            
            for selector in generic_selectors:
                paragraphs = soup.select(selector)
                if paragraphs and len(paragraphs) > 2:
                    content_paragraphs = paragraphs
                    break
        
        # Extrai e limpa o texto
        if content_paragraphs:
            content = []
            for p in content_paragraphs:
                text = clean_text(p.get_text())
                if text and len(text) > 50:  # Filtra parágrafos muito curtos
                    content.append(text)
            
            return ' '.join(content) if content else None
        
        return None
        
    except Exception as e:
        logger.error(f"Erro ao extrair conteúdo de {url}: {str(e)}")
        return None

def extract_image_from_article(url, soup=None):
    """Extrai a imagem principal do artigo"""
    try:
        if not soup:
            response = requests.get(url, headers=get_headers(), timeout=5)
            soup = BeautifulSoup(response.content, 'html.parser')
        
        # Procura por imagens em diferentes locais
        img_selectors = [
            'meta[property="og:image"]',
            'meta[name="twitter:image"]',
            'article img',
            '.content img',
            'img[class*="featured"]',
            'img[class*="main"]'
        ]
        
        for selector in img_selectors:
            img = soup.select_one(selector)
            if img:
                img_url = img.get('content') or img.get('src')
                if img_url and isinstance(img_url, str):
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        parsed_url = urlparse(url)
                        img_url = f"{parsed_url.scheme}://{parsed_url.netloc}{img_url}"
                    
                    return img_url
        
        return None
        
    except Exception as e:
        logger.error(f"Erro ao extrair imagem de {url}: {str(e)}")
        return None

def categorize_article(title, description, content):
    """Categoriza um artigo baseado no conteúdo"""
    text_to_analyze = f"{title} {description} {content}".lower()
    
    category_scores = {}
    
    for category, keywords in CATEGORY_MAPPING.items():
        score = 0
        for keyword in keywords:
            score += text_to_analyze.count(keyword.lower())
        category_scores[category] = score
    
    # Retorna a categoria com maior pontuação, ou 'general' se nenhuma se destaca
    best_category = max(category_scores.items(), key=lambda x: x[1])
    return best_category[0] if best_category[1] > 0 else 'general'

def fetch_news_from_newsapi(category='', query=''):
    """Busca notícias da NewsAPI"""
    articles = []
    
    if not NEWSAPI_KEY:
        logger.warning("NEWSAPI_KEY não configurada")
        return articles
    
    try:
        # Mapeia categorias para NewsAPI
        newsapi_categories = {
            'technology': 'technology',
            'business': 'business',
            'sports': 'sports',
            'entertainment': 'entertainment',
            'general': 'general'
        }
        
        params = {
            'apiKey': NEWSAPI_KEY,
            'pageSize': 10,
            'language': 'pt',
            'country': 'br'
        }
        
        if category and category in newsapi_categories:
            params['category'] = newsapi_categories[category]
            endpoint = f"{NEWSAPI_BASE_URL}/top-headlines"
        elif query:
            params['q'] = query
            endpoint = f"{NEWSAPI_BASE_URL}/everything"
        else:
            endpoint = f"{NEWSAPI_BASE_URL}/top-headlines"
        
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') == 'ok':
            for article_data in data.get('articles', []):
                if not article_data.get('title') or article_data.get('title') == '[Removed]':
                    continue
                
                # Extrai conteúdo completo se disponível
                full_content = article_data.get('content', '') or article_data.get('description', '')
                
                # Remove texto padrão do NewsAPI
                if full_content and '[+' in full_content:
                    full_content = full_content.split('[+')[0].strip()
                
                article = {
                    'id': f"newsapi_{hash(article_data['url'])}",
                    'title': article_data['title'],
                    'description': article_data.get('description', ''),
                    'content': full_content,
                    'url': article_data['url'],
                    'urlToImage': article_data.get('urlToImage'),
                    'publishedAt': article_data['publishedAt'],
                    'source': {
                        'name': article_data['source']['name'],
                        'id': 'newsapi'
                    },
                    'category': category or 'general',
                    'tags': [category or 'general', 'newsapi']
                }
                
                articles.append(article)
        
    except Exception as e:
        logger.error(f"Erro ao buscar notícias da NewsAPI: {str(e)}")
    
    return articles

def fetch_news_from_source(source_key, source_config):
    """Busca notícias de uma fonte específica"""
    articles = []
    
    try:
        # Busca via RSS
        feed = feedparser.parse(source_config['rss_url'])
        
        if not feed.entries:
            logger.warning(f"Nenhuma entrada encontrada no RSS de {source_config['name']}")
            return articles
        
        for entry in feed.entries[:5]:  # Limita a 5 artigos por fonte para acelerar
            try:
                # Informações básicas do RSS
                title = clean_text(entry.title)
                description = clean_text(entry.get('description', ''))
                link = entry.link
                pub_date = entry.get('published_parsed')
                
                if pub_date:
                    published_at = datetime(*pub_date[:6]).isoformat()
                else:
                    published_at = datetime.now().isoformat()
                
                # Usar descrição como conteúdo inicial para acelerar carregamento
                full_content = description
                
                # Extrai imagem do RSS primeiro
                image_url = entry.get('media_thumbnail') or entry.get('media_content')
                if isinstance(image_url, list) and image_url:
                    image_url = image_url[0].get('url') if hasattr(image_url[0], 'get') else str(image_url[0])
                elif isinstance(image_url, dict):
                    image_url = image_url.get('url')
                
                if not image_url:
                    image_url = extract_image_from_article(link)
                
                # Categoriza o artigo
                category = categorize_article(title, description, full_content)
                
                article = {
                    'id': f"{source_key}_{hash(link)}",
                    'title': title,
                    'description': description,
                    'content': full_content,
                    'url': link,
                    'urlToImage': image_url,
                    'publishedAt': published_at,
                    'source': {
                        'name': source_config['name'],
                        'id': source_key
                    },
                    'category': category,
                    'tags': [category, source_config['name'].lower()]
                }
                
                articles.append(article)
                
            except Exception as e:
                logger.error(f"Erro ao processar artigo {entry.get('title', 'Unknown')} de {source_config['name']}: {str(e)}")
                continue
        
    except Exception as e:
        logger.error(f"Erro ao buscar notícias de {source_config['name']}: {str(e)}")
    
    return articles

def update_news_cache():
    """Atualiza o cache de notícias"""
    logger.info("Iniciando atualização do cache de notícias...")
    
    all_articles = []
    
    # Busca notícias da NewsAPI primeiro (mais rápido)
    if NEWSAPI_KEY:
        logger.info("Buscando notícias da NewsAPI...")
        newsapi_articles = fetch_news_from_newsapi()
        all_articles.extend(newsapi_articles)
        time.sleep(1)
    
    # Busca notícias de todas as fontes brasileiras
    for source_key, source_config in NEWS_SOURCES.items():
        logger.info(f"Buscando notícias de {source_config['name']}...")
        articles = fetch_news_from_source(source_key, source_config)
        all_articles.extend(articles)
        time.sleep(1)  # Pausa entre requisições para não sobrecarregar os sites
    
    # Ordena por data de publicação (mais recentes primeiro)
    all_articles.sort(key=lambda x: x['publishedAt'], reverse=True)
    
    # Organiza por categoria
    by_category = {}
    for article in all_articles:
        category = article['category']
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(article)
    
    # Atualiza o cache
    news_cache['articles'] = all_articles
    news_cache['last_update'] = datetime.now()
    news_cache['by_category'] = by_category
    
    logger.info(f"Cache atualizado com {len(all_articles)} artigos")

def background_news_update():
    """Atualiza as notícias em background"""
    while True:
        try:
            update_news_cache()
            time.sleep(300)  # Atualiza a cada 5 minutos
        except Exception as e:
            logger.error(f"Erro na atualização em background: {str(e)}")
            time.sleep(60)  # Tenta novamente em 1 minuto em caso de erro

@app.route('/api/news')
def get_news():
    """Endpoint principal para buscar notícias"""
    try:
        category = request.args.get('category', '')
        query = request.args.get('q', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))
        
        # Se o cache está vazio ou muito antigo, atualiza
        if (not news_cache['articles'] or 
            not news_cache['last_update'] or 
            datetime.now() - news_cache['last_update'] > timedelta(minutes=10)):
            update_news_cache()
        
        articles = news_cache['articles']
        
        # Filtra por categoria
        if category:
            articles = news_cache['by_category'].get(category, [])
        
        # Filtra por busca
        if query:
            query_lower = query.lower()
            articles = [
                article for article in articles
                if (query_lower in article['title'].lower() or 
                    query_lower in article['description'].lower() or
                    query_lower in article.get('content', '').lower())
            ]
        
        # Paginação
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_articles = articles[start_index:end_index]
        
        response = {
            'status': 'ok',
            'totalResults': len(articles),
            'articles': paginated_articles
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Erro na API de notícias: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/article/<article_id>')
def get_article_detail(article_id):
    """Endpoint para buscar detalhes de um artigo específico"""
    try:
        for article in news_cache['articles']:
            if article['id'] == article_id:
                return jsonify(article)
        
        return jsonify({
            'status': 'error',
            'message': 'Artigo não encontrado'
        }), 404
        
    except Exception as e:
        logger.error(f"Erro ao buscar artigo {article_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/health')
def health_check():
    """Endpoint de saúde da API"""
    return jsonify({
        'status': 'ok',
        'last_update': news_cache['last_update'].isoformat() if news_cache['last_update'] else None,
        'total_articles': len(news_cache['articles'])
    })

@app.route('/')
def index():
    """Serve o arquivo HTML principal"""
    with open('index.html', 'r', encoding='utf-8') as f:
        return f.read()

if __name__ == '__main__':
    # Inicia a atualização de notícias em background
    logger.info("Iniciando servidor de notícias...")
    
    # Inicia thread de atualização em background sem bloquear
    background_thread = threading.Thread(target=background_news_update, daemon=True)
    background_thread.start()
    
    # Faz primeira atualização rápida em background
    threading.Thread(target=update_news_cache, daemon=True).start()
    
    # Inicia o servidor Flask
    app.run(host='0.0.0.0', port=5000, debug=False)