
#!/usr/bin/python3

from flask import Flask, Response, request, jsonify
import requests
import gzip
import io
import os
import urllib.parse
import subprocess
from bs4 import BeautifulSoup

app = Flask(__name__)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 9700))


@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp


def start_node_server():
    subprocess.Popen(
        ["node", "tmdb_server.js"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def fetch_and_decompress(url):
    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )
    r.raise_for_status()

    with gzip.GzipFile(fileobj=io.BytesIO(r.content)) as gz:
        return gz.read().decode("utf-8", errors="ignore")


@app.route("/getsub")
def getsub():
    try:
        url = request.args.get("url")
        name = request.args.get("name")

        if not url or not name:
            return jsonify({"error": "missing url or name"}), 400

        url = urllib.parse.unquote(url)
        name = urllib.parse.unquote(name)

        subtitle = fetch_and_decompress(url)
        ext = os.path.splitext(name)[1].lower()

        if ext == ".txt":
            return Response(subtitle, mimetype="text/plain; charset=utf-8")

        if ext == ".srt":
            clean = subtitle.replace("\r\n", "\n").strip()
            return Response(
                clean,
                mimetype="application/x-subrip; charset=utf-8",
                headers={
                    "Content-Disposition": f'attachment; filename="{name}"',
                    "X-Content-Type-Options": "nosniff"
                }
            )

        return jsonify({"error": "only .srt or .txt allowed"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/cors-url")
def cors_proxy():
    raw_url = request.args.get("url")

    if not raw_url:
        return "Missing url", 400

    url = urllib.parse.unquote(raw_url)

    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "*/*"
            },
            timeout=15
        )

        excluded = {
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection"
        }

        headers = [
            (k, v)
            for k, v in resp.headers.items()
            if k.lower() not in excluded
        ]

        return Response(resp.content, resp.status_code, headers)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def build_url(tmdb=None, imdb=None):
    if imdb:
        return f"https://ythd.org/embed/{imdb}"
    if tmdb:
        return f"https://vsembed.ru/embed/movie/{tmdb}"
    return None


def normalize_url(url):
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    return url


@app.route("/fetch")
def fetch():
    tmdb = request.args.get("tmdb")
    imdb = request.args.get("imdb")
    custom_url = request.args.get("url")

    url = custom_url if custom_url else build_url(tmdb=tmdb, imdb=imdb)

    if not url:
        return jsonify({"error": "missing tmdb, imdb, or url"}), 400

    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        iframes = []
        for iframe in soup.find_all("iframe"):
            src = normalize_url(iframe.get("src"))
            if src:
                iframes.append(src)

        return jsonify({
            "embed_url": url,
            "iframe_count": len(iframes),
            "iframes": iframes
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    start_node_server()
    app.run(host=HOST, port=PORT)
