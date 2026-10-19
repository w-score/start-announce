"""No.7 向けのイントネーション調整（W1 案, 2026-10-16 本人確認）と無音の切り詰め"""
import io, wave
import numpy as np
from voicevox_core import AccentPhrase

def mtext(ap): return ''.join(m.text for m in ap.moras)

def tune(syn, q, style, target_min_up=0.0, match_shusso=0.0, juuni='flat'):
    aps = q.accent_phrases
    # 1) 「さんぷん」+「まえわくまで」を一句にし、「まえ」まで高く「わく」で下げる（アクセント核 = 6 モーラ目「エ」）
    for i in range(len(aps) - 1):
        if mtext(aps[i]) == 'サンプン' and mtext(aps[i+1]) == 'マエワクマデ':
            joined = AccentPhrase(moras=aps[i].moras + aps[i+1].moras, accent=6,
                                  pause_mora=aps[i+1].pause_mora, is_interrogative=False)
            aps = aps[:i] + [joined] + aps[i+2:]
            break
    # 1b) 10時〜13時: 「じゅう」+「にじ…」が別の句に割れて「に」が高くなるのを直す
    #     じゅ↓うじ(1)、じゅうい↓ちじ(4)、じゅうに↓じ(4)、じゅうさ↓んじ(4)
    merged = []
    i = 0
    while i < len(aps):
        ap = aps[i]
        if mtext(ap) == 'ジュウ' and i + 1 < len(aps) and ap.pause_mora is None and \
           any(mtext(aps[i+1]).startswith(k) for k in ('イチジ', 'ニジ', 'サンジ')):
            nxt = aps[i+1]
            merged.append(AccentPhrase(moras=ap.moras + nxt.moras, accent=4,
                                       pause_mora=nxt.pause_mora, is_interrogative=False))
            i += 2
            continue
        if mtext(ap).startswith('ジュウジ'):
            ap.accent = 1
        merged.append(ap); i += 1
    aps = merged
    q.accent_phrases = syn.replace_mora_data(aps, style)
    # 2) 「く↓じ」をはっきり（9 時のとき）
    for ap in q.accent_phrases:
        if mtext(ap) == 'クジ':
            ap.moras[0].pitch += 0.18; ap.moras[1].pitch -= 0.22; ap.moras[1].vowel_length *= 1.15
    # 2b) 「じゅうにじ」: じゅうに(高・平ら)→じ(下げて短く)。2 回目も同じ高さ（2026-10-18）
    #     さらに「にじゅう○ぷん」の「に」も「じゅうに」と同じ高さにそろえる
    H = None
    for ap in q.accent_phrases:
        if mtext(ap).startswith('ジュウニジ'):
            if H is None:
                H = ap.moras[2].pitch + 0.05
            if juuni == 'step':   # じゅう(高) → に(下げ) → じ(さらに下げ)
                ap.moras[0].pitch = H; ap.moras[1].pitch = H
                ap.moras[2].pitch = H - 0.12
                ap.moras[3].pitch = H - 0.30
            else:                 # じゅうに(平ら) → じ(下げ)
                for m in ap.moras[:3]: m.pitch = H
                ap.moras[3].pitch = H - 0.25
            ap.moras[3].vowel_length *= 0.8
    # 2c) 「にじゅう○ぷん」の「に」をわずかに高く・少し強く
    for ap in q.accent_phrases:
        if mtext(ap).startswith('ニジュウ'):
            top = max(m.pitch for m in ap.moras[:3])
            ap.moras[0].pitch = H if H is not None else top + 0.18
            ap.moras[0].vowel_length *= 1.15
    # 2d) 出走時刻（「なりました。」の後〜「出走の」の前）を気持ちゆっくり・少し高く（2026-10-18）
    aps = q.accent_phrases
    try:
        i0 = next(i for i, ap in enumerate(aps) if mtext(ap) == 'ナリマシタ') + 1
        i1 = next(i for i, ap in enumerate(aps) if mtext(ap) == 'シュッソオノ')
        for ap in aps[i0:i1]:
            for m in ap.moras:
                m.vowel_length *= 1.12
                if m.consonant_length: m.consonant_length *= 1.12
                if m.pitch > 0: m.pitch += 0.04
    except StopIteration:
        pass
    # 3) 出走時刻の「○分」（「出走の」の直前の句）をわずかに高く
    aps = q.accent_phrases
    for i in range(len(aps) - 1):
        if mtext(aps[i+1]) == 'シュッソオノ':
            up = target_min_up
            if match_shusso:
                # 「出走の」の平均の高さに合わせる（match_shusso は 0〜1 の割合）
                a = [m.pitch for m in aps[i].moras if m.pitch > 0]
                b = [m.pitch for m in aps[i+1].moras if m.pitch > 0]
                up = match_shusso * (sum(b)/len(b) - sum(a)/len(a))
            for m in aps[i].moras:
                if m.pitch > 0: m.pitch += up
    return q

def trim_pauses(wav_bytes, max_gap=0.12, thresh=0.01, min_gap=0.15):
    """max_gap は数値か、無音区間ごとのリスト（足りない分は最後の値）"""
    gaps = list(max_gap) if isinstance(max_gap, (list, tuple)) else [max_gap]
    gi = 0
    """文中の無音（min_gap 秒以上）を max_gap 秒に切り詰める。先頭・末尾の無音はそのまま。"""
    with wave.open(io.BytesIO(wav_bytes)) as w:
        sr, n, sw = w.getframerate(), w.getnframes(), w.getsampwidth()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    env = np.abs(x)
    win = int(sr * 0.01)
    sm = np.convolve(env, np.ones(win) / win, mode='same')
    silent = sm < thresh
    # 無音区間を列挙
    out, i, N = [], 0, len(x)
    first_voice = np.argmax(~silent); last_voice = N - np.argmax(~silent[::-1])
    while i < N:
        if silent[i]:
            j = i
            while j < N and silent[j]: j += 1
            length = (j - i) / sr
            if i > first_voice and j < last_voice and length >= min_gap:
                keep = int(gaps[min(gi, len(gaps)-1)] * sr); gi += 1
                # 前後を少しずつ残して中央を落とす
                out.append(x[i:i + keep // 2]); out.append(x[j - (keep - keep // 2):j])
            else:
                out.append(x[i:j])
            i = j
        else:
            j = i
            while j < N and not silent[j]: j += 1
            out.append(x[i:j]); i = j
    y = np.concatenate(out)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def pause_positions(q):
    """audio_query の pause_mora の (開始秒, 終了秒) を返す"""
    t = q.pre_phoneme_length
    out = []
    for ap in q.accent_phrases:
        for m in ap.moras:
            t += (m.consonant_length or 0) + m.vowel_length
        if ap.pause_mora:
            pm = ap.pause_mora
            L = pm['vowel_length'] if isinstance(pm, dict) else pm.vowel_length
            out.append((t, t + L)); t += L
    return out


def trim_pauses_exact(wav_bytes, q, gaps, thresh=0.006, fade=0.01, thresh_pre=None):
    """pause_mora の位置を基準に、その前後の減衰部分も含めた「ほぼ無音」を gaps[i] 秒に切り詰める"""
    with wave.open(io.BytesIO(wav_bytes)) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    env = np.convolve(np.abs(x), np.ones(int(sr * 0.01)) / int(sr * 0.01), mode='same')
    cuts = []
    for (a, b), g in zip(pause_positions(q), gaps):
        i = int(a * sr); j = int(b * sr)
        tp = thresh_pre if thresh_pre is not None else thresh
        while i > 0 and env[i - 1] < tp: i -= 1               # 前の減衰部分
        while j < len(x) and env[j] < thresh: j += 1          # 後の立ち上がり前
        keep = int(g * sr)
        if j - i > keep: cuts.append((i, j, keep))
    pieces, pos, nf = [], 0, int(fade * sr)
    for i, j, keep in cuts:
        head = x[pos:i + keep // 2].copy()
        if nf and len(head) > nf: head[-nf:] *= np.linspace(1, 0, nf)
        pieces.append(head)
        tail = x[j - (keep - keep // 2):j].copy()
        pieces.append(tail); pos = j
    pieces.append(x[pos:])
    y = np.concatenate(pieces)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def target_span(q):
    """出走時刻部分（なりました。の後〜出走の の前）の (開始秒, 終了秒)"""
    t = q.pre_phoneme_length; start = end = None; prev = None
    for ap in q.accent_phrases:
        if prev == 'ナリマシタ': start = t
        if mtext(ap) == 'シュッソオノ': end = t
        for m in ap.moras:
            t += (m.consonant_length or 0) + m.vowel_length
        if ap.pause_mora:
            pm = ap.pause_mora
            t += pm['vowel_length'] if isinstance(pm, dict) else pm.vowel_length
        prev = mtext(ap)
    return start, end


def emphasize_target(wav_bytes, q, gain_db=1.5, ramp=0.03):
    """出走時刻部分の音量を少し上げる（合成前の波形に対して。間の切り詰めより前に適用）"""
    start, end = target_span(q)
    if start is None or end is None: return wav_bytes
    with wave.open(io.BytesIO(wav_bytes)) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    g = 10 ** (gain_db / 20); env = np.ones(len(x), dtype=np.float32)
    i, j, r = int(start * sr), int(end * sr), int(ramp * sr)
    env[i:j] = g
    env[max(0, i - r):i] = np.linspace(1, g, min(r, i))
    env[j:j + r] = np.linspace(g, 1, min(r, len(x) - j))
    y = np.clip(x * env, -1, 1)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((y * 32767).astype(np.int16).tobytes())
    return buf.getvalue()
