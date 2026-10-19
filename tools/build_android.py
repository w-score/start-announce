#!/usr/bin/env python3
"""
Android 用: 音声ファイルをすべて埋め込んだ 1 ファイルの HTML を作る。

  python build_android.py --pwa ../pwa --out start_announce_android.html --voice no7 --voice ryusei

  --pwa   : index.html と clips/ があるフォルダ（iOS 用 PWA フォルダそのもの）
  --voice : 埋め込む音声（複数可）。1 種類だけにすればファイルが半分になる。

できた HTML をスマホに送り（Google ドライブ、メール添付、USB など）、Chrome で開く。
"""
import argparse, base64, json, os, re

ap = argparse.ArgumentParser()
ap.add_argument("--pwa", default="../pwa")
ap.add_argument("--out", default="start_announce_android.html")
ap.add_argument("--voice", action="append")
a = ap.parse_args()

html = open(os.path.join(a.pwa, "index.html"), encoding="utf-8").read()
index = json.load(open(os.path.join(a.pwa, "clips", "index.json"), encoding="utf-8"))
ext = index.get("ext", "mp3")
mime = "audio/mpeg" if ext == "mp3" else "audio/wav"

m = re.search(r"const VOICES = \(EMB && EMB\.voices\) \|\| \[(.*?)\];", html, re.S)
all_voices = [{"id": i, "label": l} for i, l in re.findall(r"id: '([^']+)',\s*label: '([^']+)'", m.group(1))]
voices = [v for v in all_voices if not a.voice or v["id"] in a.voice]

clips = {}
for v in voices:
    for c in index["clips"]:
        path = os.path.join(a.pwa, "clips", v["id"], f"{c['key']}.{ext}")
        if os.path.exists(path):
            clips[f"{v['id']}/{c['key']}"] = base64.b64encode(open(path, "rb").read()).decode("ascii")
        else:
            print("missing:", path)

payload = json.dumps({"index": index, "voices": voices, "clips": clips, "mime": mime}, ensure_ascii=False)
inject = f"<script>window.EMBEDDED = {payload};</script>\n  <script>"
out = html.replace("<script>", inject, 1)
# PWA 専用のタグは外す
out = re.sub(r'\s*<link rel="manifest"[^>]*>', "", out)
out = re.sub(r'\s*<link rel="apple-touch-icon"[^>]*>', "", out)
out = out.replace("<title>スタートエリア アナウンス（オフライン）</title>", "<title>スタートエリア アナウンス（Android・音声内蔵）</title>")
open(a.out, "w", encoding="utf-8").write(out)
print(f"{a.out}: {os.path.getsize(a.out)/1e6:.1f} MB, {len(clips)} clips, voices={[v['id'] for v in voices]}")
