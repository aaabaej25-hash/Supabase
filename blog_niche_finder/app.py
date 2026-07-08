# -*- coding: utf-8 -*-
"""
blog_niche_finder / app.py

경쟁 블로그 분석 + 틈새 주제 추천 웹앱
실행: python app.py  ->  http://127.0.0.1:5000
"""

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import io
import os
import subprocess
import importlib
import contextlib

try:
    importlib.import_module("flask")
except ImportError:
    print("[설치] flask 설치 중...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])

from flask import Flask, request, render_template, send_from_directory

import config
import main  # noqa: E402  (main import 시 필요 라이브러리 자동 설치가 수행된다)

app = Flask(__name__)

MAX_LINKS = 5


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", max_links=MAX_LINKS)


@app.route("/analyze", methods=["POST"])
def analyze():
    urls = []
    for i in range(1, MAX_LINKS + 1):
        url = request.form.get(f"url{i}", "").strip()
        if url:
            urls.append(url)

    log_buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(log_buffer):
            result = main.run_pipeline(extra_links=urls or None)
    except Exception as e:
        log_buffer.write(f"\n[오류] 파이프라인 실행 중 예외 발생: {e}\n")
        result = {"has_data": False, "niche_items": [], "output_paths": {}}

    output_files = {
        key: os.path.basename(path)
        for key, path in result["output_paths"].items()
    }

    return render_template(
        "result.html",
        has_data=result["has_data"],
        niche_items=result["niche_items"],
        output_files=output_files,
        log_text=log_buffer.getvalue(),
        input_urls=urls,
    )


@app.route("/output/<path:filename>")
def output_file(filename):
    return send_from_directory(config.OUTPUT_DIR, filename)


if __name__ == "__main__":
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    print("웹앱을 시작합니다: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
