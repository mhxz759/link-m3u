# Portal de Notícias

Portal de notícias completo que combina web scraping de sites brasileiros confiáveis com a NewsAPI.

## Recursos

- **Fontes confiáveis**: G1, UOL, CNN Brasil, Folha, Estadão
- **NewsAPI**: Integração com API de notícias internacionais
- **Notícias completas**: Leia tudo sem sair do portal
- **Interface moderna**: Design responsivo e modo escuro/claro
- **Sistema de favoritos**: Salve notícias interessantes
- **Busca e filtros**: Por categoria e palavra-chave
- **Atualizações automáticas**: A cada 5 minutos

## Como executar

### 1. Instalar dependências
```bash
pip install flask requests beautifulsoup4 feedparser python-dateutil flask-cors
```

### 2. Configurar NewsAPI (opcional)
- Obtenha uma chave gratuita em: https://newsapi.org
- Configure a variável de ambiente:
```bash
export NEWSAPI_KEY="sua_chave_aqui"
```

### 3. Executar o servidor
```bash
python server.py
```

### 4. Acessar o portal
Abra seu navegador em: http://localhost:5000

## Estrutura do projeto

- `index.html` - Interface completa (HTML + CSS + JavaScript)
- `server.py` - Backend Python com web scraping e API
- `pyproject.toml` - Dependências do projeto

## Funcionalidades

- ✅ Web scraping de sites brasileiros
- ✅ Integração com NewsAPI
- ✅ Notícias completas no próprio portal
- ✅ Sistema de favoritos
- ✅ Busca e filtros
- ✅ Design responsivo
- ✅ Modo escuro/claro
- ✅ Atualizações automáticas

## Tecnologias

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Backend**: Python, Flask
- **Web Scraping**: BeautifulSoup, Feedparser
- **APIs**: NewsAPI, RSS Feeds

## Suporte

O portal funciona com ou sem a NewsAPI. Mesmo sem a chave da API, você ainda terá acesso às notícias dos sites brasileiros através de web scraping.