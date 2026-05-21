#!/usr/bin/env python3
"""Gera um artigo sobre forró usando a Gemini API e salva como post Jekyll."""

from google import genai
from google.genai import types
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

POSTS_DIR = Path("_posts")
TOPICS_FILE = Path("scripts/topics.json")
MODEL = "gemini-1.5-flash"

SYSTEM_PROMPT = """Você é um especialista em forró e cultura nordestina brasileira, com décadas de pesquisa e paixão pelo tema.

Escreva artigos informativos, envolventes e bem pesquisados sobre forró para o site Mundo do Forró.

Diretrizes:
- Formato: Markdown puro (sem bloco de código, apenas o conteúdo)
- Tamanho: 900 a 1200 palavras
- Estrutura: Use ## para H2 e ### para H3. Inclua pelo menos 4 seções
- Tom: Apaixonado, acessível, informativo. Como um amigo que sabe muito sobre o tema
- SEO: Use as palavras-chave principais nas primeiras 100 palavras e nos subtítulos
- Inclua fatos históricos concretos e curiosidades que surpreendam o leitor
- Termine com uma seção de FAQ ou conclusão que convide o leitor a explorar mais o site
- NÃO inclua o título H1 no corpo — ele já está no frontmatter
- NÃO use linguagem excessivamente formal ou acadêmica"""


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


def generate_article(topic: dict) -> str:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = (
        f"Escreva um artigo completo sobre: **{topic['title']}**\n\n"
        f"Tópicos a abordar: {topic['description']}\n\n"
        f"Lembre-se: não inclua o título H1 no corpo, comece direto com a introdução."
    )
    response = client.models.generate_content(
        model=MODEL,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        contents=prompt,
    )
    return response.text


def save_article(topic: dict, content: str) -> Path:
    POSTS_DIR.mkdir(exist_ok=True)
    date = datetime.now().strftime('%Y-%m-%d')
    slug = slugify(topic['title'])
    filepath = POSTS_DIR / f"{date}-{slug}.md"

    # Escape aspas no título para o frontmatter
    safe_title = topic['title'].replace('"', '\\"')
    safe_desc = topic['description'][:160].replace('"', '\\"')

    frontmatter = f"""---
layout: post
title: "{safe_title}"
date: {date}
categories: {topic.get('category', 'forró')}
description: "{safe_desc}"
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
