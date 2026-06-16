#!/usr/bin/env python3
"""Gera um artigo sobre forró via Groq API e salva como post Jekyll."""

import json
import os
import re
import sys
import random
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path

POSTS_DIR = Path("_posts")
TOPICS_FILE = Path("scripts/topics.json")
MODEL = "llama-3.3-70b-versatile"
API_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """Você é Renato Alencar, jornalista musical nascido em Recife e apaixonado por forró desde criança. Passou anos entrevistando artistas, pesquisando acervos e viajando pelo Nordeste para documentar a cultura forrozeira. Escreve para o Mundo do Forró com a autoridade de quem viveu o tema de perto.

Escreva artigos profundos, autorais e bem fundamentados sobre forró para o site Mundo do Forró.

REGRAS OBRIGATÓRIAS:
- Formato: Markdown puro (sem bloco de código, apenas o conteúdo)
- Tamanho: 1500 a 2000 palavras — artigos curtos serão rejeitados
- Estrutura: Use ## para H2 e ### para H3. Inclua pelo menos 5 seções substantivas
- Tom: Pessoal e apaixonado, como um especialista que conta histórias reais. Evite generalidades
- Cite fatos verificáveis: anos, nomes de álbuns, títulos de músicas, cidades, datas de shows históricos
- Cada seção deve ter pelo menos 3 parágrafos densos com informações específicas
- Use anedotas e detalhes concretos que só quem conhece o assunto a fundo saberia
- Termine com uma seção "Para ouvir e explorar" com sugestões concretas de músicas/álbuns (não links)
- NÃO inclua o título H1 no corpo — ele já está no frontmatter
- NÃO escreva FAQs genéricos ("O que é forró? R: É um gênero musical...")
- NÃO use frases vagas como "é importante ressaltar" ou "como todos sabem"
- NÃO repita a introdução no final com outras palavras"""


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
        parts = post.stem.split('-')
        if len(parts) > 3:
            slug = '-'.join(parts[3:])
            used.add(slug)
    return used


def get_image_url(topic: dict) -> str:
    seed = slugify(topic['title'])[:20]
    return f"https://picsum.photos/seed/{seed}/1200/630"


def generate_article(topic: dict) -> str:
    api_key = os.environ["GROQ_API_KEY"]

    prompt = (
        f"Escreva um artigo completo e aprofundado sobre: **{topic['title']}**\n\n"
        f"Ângulos obrigatórios a cobrir: {topic['description']}\n\n"
        f"Lembre-se:\n"
        f"- Comece direto com um parágrafo de abertura envolvente, sem título H1\n"
        f"- Cite nomes reais, datas, álbuns e músicas específicas\n"
        f"- Mínimo de 1500 palavras\n"
        f"- Termine com 'Para ouvir e explorar' com sugestões concretas"
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
