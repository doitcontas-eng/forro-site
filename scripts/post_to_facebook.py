#!/usr/bin/env python3
"""Posta o artigo mais recente na página do Facebook via Graph API."""

import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


POSTS_DIR = Path("_posts")
API_URL = "https://graph.facebook.com/v19.0"

EMOJIS = ["🎵", "🪗", "🎶", "🥁", "🎉", "🔥", "💃", "🕺"]


def get_latest_post() -> dict | None:
    posts = sorted(POSTS_DIR.glob("*.md"), reverse=True)
    if not posts:
        return None

    post = posts[0]
    title = ""
    description = ""
    date = ""

    with open(post, encoding="utf-8") as f:
        in_frontmatter = False
        for line in f:
            line = line.rstrip()
            if line == "---":
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter:
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip('"')
                elif line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"')
                elif line.startswith("date:"):
                    date = line.split(":", 1)[1].strip()

    # Monta URL do artigo a partir do nome do arquivo
    parts = post.stem.split("-")
    year, month, day = parts[0], parts[1], parts[2]
    slug = "-".join(parts[3:])
    url = f"https://mundodoforro.com.br/{year}/{month}/{day}/{slug}/"

    return {"title": title, "description": description, "url": url, "date": date}


def build_message(post: dict) -> str:
    import random
    emoji = random.choice(EMOJIS)
    return (
        f"{emoji} {post['title']}\n\n"
        f"{post['description']}\n\n"
        f"Leia o artigo completo:\n{post['url']}"
    )


def post_to_facebook(message: str, page_id: str, token: str) -> dict:
    payload = json.dumps({
        "message": message,
        "access_token": token
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{API_URL}/{page_id}/feed",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"Erro HTTP {e.code}: {body}")
        raise


def main():
    page_id = os.environ["FB_PAGE_ID"]
    token = os.environ["FB_PAGE_TOKEN"]

    post = get_latest_post()
    if not post:
        print("Nenhum artigo encontrado.")
        return

    print(f"Postando: {post['title']}")
    message = build_message(post)
    result = post_to_facebook(message, page_id, token)
    print(f"Postado com sucesso! ID: {result.get('id')}")


if __name__ == "__main__":
    main()
