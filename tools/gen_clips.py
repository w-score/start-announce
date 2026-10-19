#!/usr/bin/env python3
"""
VOICEVOX（PC 版アプリ）の HTTP API で、毎分のスタート呼び出し音声を一括生成する。

使い方（VOICEVOX アプリを起動しておく。標準では http://127.0.0.1:50021）:
  python gen_clips.py --start 09:00 --end 13:00 --lead 3 --style 30 --out clips/no7
  python gen_clips.py --start 09:00 --end 13:00 --lead 3 --style 13 --out clips/ryusei

  --style : VOICEVOX のスタイル ID（30 = No.7 アナウンス、13 = 青山龍星 ノーマル、14 = 冥鳴ひまり）
            一覧は  curl http://127.0.0.1:50021/speakers  で確認できる。
  --speed : 話速（1.0 が標準。0.9 で少しゆっくり）
  mp3 化には ffmpeg が必要（PATH に通しておく）。ffmpeg が無ければ wav のまま出力する。

出力: <out>/HHMM.mp3 と <out>/../index.json（index.html が読む一覧）
"""
import argparse, json, os, shutil, subprocess, sys, urllib.parse, urllib.request

LEAD_YOMI = {2: "にふんまえ", 3: "さんぷんまえ", 4: "よんぷんまえ", 5: "ごふんまえ"}


def announce_text(h, m, lead):
    th, tm = divmod(h * 60 + m + lead, 60)
    th %= 24
    now_t = f"{h}時" if m == 0 else f"{h}時{m}分"
    tgt_t = f"{th}時" if tm == 0 else f"{th}時{tm}分"
    display = f"{now_t}になりました。{tgt_t}出走の方は、{lead}分前枠までお越しください。"
    # 読み上げ用: 誤読しやすい語を仮名にし、読点で間を作る
    speech = f"{now_t}になりました。{tgt_t}、出走のかたは、{LEAD_YOMI[lead]}枠まで、お越しください。"
    return display, speech


def post(url, data=None):
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="09:00")
    ap.add_argument("--end", default="13:00")
    ap.add_argument("--lead", type=int, default=3, choices=[2, 3, 4, 5])
    ap.add_argument("--style", type=int, default=30)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--host", default="http://127.0.0.1:50021")
    ap.add_argument("--out", default="clips/no7")
    a = ap.parse_args()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("注意: ffmpeg が見つからないため wav で出力します（サイズが大きくなります）", file=sys.stderr)

    os.makedirs(a.out, exist_ok=True)
    sh, sm = map(int, a.start.split(":"))
    eh, em = map(int, a.end.split(":"))
    index = []
    for t in range(sh * 60 + sm, eh * 60 + em):
        h, m = divmod(t, 60)
        key = f"{h:02d}{m:02d}"
        display, speech = announce_text(h, m, a.lead)
        index.append({"key": key, "text": display})
        out = os.path.join(a.out, key + (".mp3" if ffmpeg else ".wav"))
        if os.path.exists(out):
            continue
        q = json.loads(post(f"{a.host}/audio_query?" + urllib.parse.urlencode({"text": speech, "speaker": a.style})))
        q["speedScale"] = a.speed
        q["prePhonemeLength"] = 0.4   # 頭切れ防止（Bluetooth スピーカー対策）
        q["postPhonemeLength"] = 0.3
        wav = post(f"{a.host}/synthesis?" + urllib.parse.urlencode({"speaker": a.style}),
                   json.dumps(q).encode("utf-8"))
        if ffmpeg:
            subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", "pipe:0", "-ac", "1", "-ar", "24000",
                            "-b:a", "48k", out], input=wav, check=True)
        else:
            open(out, "wb").write(wav)
        print(key, display, flush=True)

    idx_path = os.path.join(os.path.dirname(os.path.abspath(a.out)), "index.json")
    json.dump({"lead": a.lead, "start": a.start, "end": a.end, "ext": "mp3" if ffmpeg else "wav", "clips": index},
              open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("index:", idx_path)


if __name__ == "__main__":
    main()
