#!/usr/bin/env python3
"""Gera um artigo sobre forró via Groq API e salva como post Jekyll."""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

POSTS_DIR = Path("_posts")
TOPICS_FILE = Path("scripts/topics.json")
MODEL = "llama-3.3-70b-versatile"
API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """Você é Renato Alencar, jornalista musical nascido em Recife em 1978. Formado em Jornalismo pela UFPE, trabalhou na Rádio Jornal do Commercio nos anos 2000, entrevistou artistas como Dominguinhos, Elba Ramalho e Flávio José, e percorreu o interior do Nordeste documentando festas juninas e forró pé de serra. Hoje mantém o Mundo do Forró, o maior blog independente de forró do Brasil.

Escreva artigos profundos, autorais e bem fundamentados sobre forró para o site Mundo do Forró.

REGRAS OBRIGATÓRIAS DE CONTEÚDO:
- Formato: Markdown puro (sem bloco de código, apenas o conteúdo)
- Tamanho: 1800 a 2200 palavras — artigos curtos serão rejeitados
- Estrutura: Use ## para H2 e ### para H3. Inclua pelo menos 5 seções substantivas
- Tom: Pessoal e apaixonado. Comece pelo menos 2 seções com uma memória pessoal sua ("Lembro de quando...", "Em 2003, fui a Caruaru e...", "Num arquivo de rádio que pesquisei em Recife...")
- Cite fatos verificáveis: anos exatos, nomes de álbuns, títulos de músicas, cidades, gravadoras, datas de shows históricos
- Cada seção deve ter pelo menos 3 parágrafos densos com informações específicas
- Use anedotas e detalhes concretos que só quem conhece o assunto a fundo saberia
- Em pelo menos 2 pontos do artigo, faça referência a fontes como: "segundo o pesquisador Câmara Cascudo", "como registrou o Museu do Forró em Fortaleza", "de acordo com a Enciclopédia da Música Brasileira", "o sociólogo Hermano Vianna documentou que..."
- Termine com uma seção "Para ouvir e explorar" com sugestões concretas de músicas/álbuns com ano de lançamento

REGRAS OBRIGATÓRIAS DE FORMATO:
- NÃO inclua o título H1 no corpo — ele já está no frontmatter
- NÃO escreva FAQs genéricos ("O que é forró? R: É um gênero musical...")
- NÃO use frases vagas como "é importante ressaltar", "como todos sabem", "vale destacar que", "não podemos deixar de mencionar"
- NÃO repita a introdução no final com outras palavras
- NÃO use listas com bullet points genéricos — prefira parágrafos narrativos
- SEMPRE termine cada seção com uma observação pessoal sua ou uma anedota de reportagem"""


def slugify(text: str) -> str:
    text = text.lower()
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s]+', '-', text.strip())
    return text[:80]


def load_topics() -> list:
    with open(TOPICS_FILE, encoding='utf-8') as f:
        return json.load(f)


def get_used_slugs() -> set:
    used = set()
    for post in POSTS_DIR.glob('*.md'):
        # slug pelo nome do arquivo
        parts = post.stem.split('-')
        if len(parts) > 3:
            used.add('-'.join(parts[3:]))
        # slug pelo título no frontmatter (evita duplicatas mesmo com nomes de arquivo diferentes)
        try:
            for line in post.read_text(encoding='utf-8').split('\n'):
                if line.startswith('title:'):
                    title = line.split(':', 1)[1].strip().strip('"')
                    used.add(slugify(title))
                    break
        except Exception:
            pass
    return used


WIKIMEDIA_IMAGES = {
    "luiz gonzaga": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Luiz_Gonzaga_1973.jpg/1200px-Luiz_Gonzaga_1973.jpg",
    "sanfona": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Gaita_de_foles_-_geograph.org.uk_-_1008.jpg/1200px-Gaita_de_foles_-_geograph.org.uk_-_1008.jpg",
    "acordeao": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Accordion_player.jpg/1200px-Accordion_player.jpg",
    "zabumba": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/32/Zabumba.jpg/1200px-Zabumba.jpg",
    "festa junina": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Festa_junina_2.jpg/1200px-Festa_junina_2.jpg",
    "sao joao": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Festa_de_S%C3%A3o_Jo%C3%A3o_-_Caruaru.jpg/1200px-Festa_de_S%C3%A3o_Jo%C3%A3o_-_Caruaru.jpg",
    "nordeste": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/Caatinga2.jpg/1200px-Caatinga2.jpg",
    "danca": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e9/Forra_couple.jpg/1200px-Forra_couple.jpg",
    "triangulo": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Triangle_percussion_instrument.jpg/1200px-Triangle_percussion_instrument.jpg",
    "baiao": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Luiz_Gonzaga_1973.jpg/1200px-Luiz_Gonzaga_1973.jpg",
}

def get_image_url(topic: dict) -> str:
    title_lower = topic['title'].lower()
    for keyword, url in WIKIMEDIA_IMAGES.items():
        if keyword in title_lower:
            return url
    seed = slugify(topic['title'])[:20]
    return f"https://picsum.photos/seed/{seed}/1200/630"


def generate_article(topic: dict) -> str:
    api_key = os.environ["GROQ_API_KEY"]

    prompt = (
        f"Escreva um artigo completo e aprofundado sobre: **{topic['title']}**\n\n"
        f"Ângulos obrigatórios a cobrir: {topic['description']}\n\n"
        f"Instruções:\n"
        f"- Comece com um parágrafo de abertura forte e pessoal — uma memória sua, uma cena vivida, ou um detalhe surpreendente\n"
        f"- Cite nomes reais, datas exatas, nomes de álbuns e músicas específicas\n"
        f"- Mencione pelo menos 2 fontes acadêmicas ou institucionais (pesquisadores, museus, enciclopédias)\n"
        f"- Inclua pelo menos 2 memórias pessoais suas como jornalista (entrevistas, viagens, pesquisas em arquivos)\n"
        f"- Mínimo de 1800 palavras\n"
        f"- Termine com 'Para ouvir e explorar' com álbuns, músicas e ano de lançamento"
    )

    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 3500,
        "temperature": 0.8
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "forro-bot/1.0"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"Erro HTTP {e.code}: {body}")
        raise

    return data["choices"][0]["message"]["content"]


def save_article(topic: dict, content: str) -> Path:
    POSTS_DIR.mkdir(exist_ok=True)
    date = datetime.now().strftime('%Y-%m-%d')
    slug = slugify(topic['title'])
    filepath = POSTS_DIR / f"{date}-{slug}.md"

    safe_title = topic['title'].replace('"', '\\"')
    safe_desc = topic['description'][:160].replace('"', '\\"')
    image_url = get_image_url(topic)
    image_line = f'\nimage: "{image_url}"' if image_url else ""

    frontmatter = f"""---
layout: post
title: "{safe_title}"
date: {date}
author: "Renato Alencar"
categories: {topic.get('category', 'forró')}
description: "{safe_desc}"{image_line}
---

"""
    filepath.write_text(frontmatter + content, encoding='utf-8')
    return filepath


def main():
    topics = load_topics()
    used = get_used_slugs()

    available = [t for t in topics if slugify(t['title']) not in used]

    if not available:
        print("Todos os tópicos já foram usados! Adicione mais em scripts/topics.json")
        sys.exit(0)

    topic = available[0]
    print(f"Gerando artigo: {topic['title']}")

    content = generate_article(topic)
    filepath = save_article(topic, content)

    print(f"Artigo salvo: {filepath}")
    print(f"Tópicos restantes: {len(available) - 1}")


if __name__ == '__main__':
    main()
