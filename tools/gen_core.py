#!/usr/bin/env python3
"""voicevox_core (Python) で毎分アナウンスを一括生成する（作業環境用）。"""
import argparse, json, os, subprocess, sys
from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
from tune import tune, trim_pauses_exact, emphasize_target

def announce_text(h, m, lead):
    th, tm = divmod(h * 60 + m + lead, 60)
    th %= 24
    now_t = f"{h}時" if m == 0 else f"{h}時{m}分"
    tgt_t = f"{th}時" if tm == 0 else f"{th}時{tm}分"
    lead_yomi = {2: "にふんまえ", 3: "さんぷんまえ", 4: "よんぷんまえ", 5: "ごふんまえ"}[lead]
    display = f"{now_t}になりました。{tgt_t}出走の方は、{lead}分前枠までお越しください。"
    speech = f"{now_t}になりました。{tgt_t}、出走のかたは、{lead_yomi}枠まで、お越しください。"
    return display, speech

ap = argparse.ArgumentParser()
ap.add_argument("--start", default="08:30")
ap.add_argument("--end", default="13:30")
ap.add_argument("--lead", type=int, default=3)
ap.add_argument("--style", type=int, default=30)
ap.add_argument("--vvm", default="models/6.vvm")
ap.add_argument("--out", default="clips")
ap.add_argument("--speed", type=float, default=1.0)
ap.add_argument("--tuned", action="store_true", help="2026-10-16 決定のイントネーション調整と間の切り詰めを適用")
a = ap.parse_args()

ort = Onnxruntime.load_once(filename="voicevox_onnxruntime-linux-x64-1.17.3/lib/libvoicevox_onnxruntime.so.1.17.3")
syn = Synthesizer(ort, OpenJtalk("open_jtalk_dic_utf_8-1.11"))
with VoiceModelFile.open(a.vvm) as m:
    syn.load_voice_model(m)

os.makedirs(a.out, exist_ok=True)
sh, sm = map(int, a.start.split(":"))
eh, em = map(int, a.end.split(":"))
index = []
for t in range(sh * 60 + sm, eh * 60 + em):
    h, m = divmod(t, 60)
    key = f"{h:02d}{m:02d}"
    display, speech = announce_text(h, m, a.lead)
    index.append({"key": key, "text": display})
    mp3 = os.path.join(a.out, key + ".mp3")
    if os.path.exists(mp3):
        continue
    q = syn.create_audio_query(speech, a.style)
    if a.tuned:
        tm = (h * 60 + m + a.lead) % 60
        q = tune(syn, q, a.style, match_shusso=(0.4 if tm < 10 else 0.75))  # 分が一桁の出走時刻は上げ幅半分
    q.speed_scale = a.speed
    q.pre_phoneme_length = 0.4
    q.post_phoneme_length = 0.3
    wav = syn.synthesis(q, a.style)
    if a.tuned:
        wav = emphasize_target(wav, q, gain_db=1.5)            # 出走時刻を少し強く
        wav = trim_pauses_exact(wav, q, [0.35, 0.05, 0.10, 0.05])
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", "pipe:0", "-ac", "1", "-ar", "24000",
                    "-b:a", "48k", mp3], input=wav, check=True)
    print(key, display, flush=True)

json.dump({"lead": a.lead, "start": a.start, "end": a.end, "ext": "mp3", "clips": index},
          open(os.path.join(a.out, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
