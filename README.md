# スタートエリア アナウンス（オフライン・事前生成音声版）

オリエンテーリング大会のスタート地区で、毎分「○時○分になりました。○時○分出走の方は、3分前枠までお越しください。」を自動で流すツールです。
音声は VOICEVOX で事前に生成した mp3 を再生するだけなので、圏外でも動きます。

## フォルダ構成

```
start-announce/
  index.html            画面と再生ロジック（iOS / Android 共通）
  sw.js                 Service Worker（オフライン用キャッシュ）
  manifest.webmanifest  ホーム画面追加用
  icon-180.png, icon-512.png
  clips/
    index.json          収録した時刻の一覧（呼び出しの分数・範囲・本文）
    no7/HHMM.mp3        No.7「アナウンス」スタイル（VOICEVOX:No.7）
    ryusei/HHMM.mp3     青山龍星「ノーマル」（VOICEVOX:青山龍星）
```

収録範囲は 09:20〜13:30（毎分、計 251 本、声は No.7 のみ）、呼び出しは 3 分前枠です。
範囲外の時刻は端末内蔵の音声合成で代替します（品質は落ちます）。

## iPhone での使い方（PWA）

iPhone は「ファイルをそのまま開く」方法では JavaScript が動かないため、https のサイトに置いて使います。
ご自身の GitHub Pages に `start-announce/` フォルダごと置くのが簡単です。

1. GitHub Pages のリポジトリに `start-announce/` をコピーして push する。
   例: `https://<ユーザー名>.github.io/start-announce/`
2. **ネットのある所で** iPhone の Safari でその URL を開く。
3. 「音声」で使う声を選び、「オフライン用に保存」を押す（300 本、十数 MB。1〜2 分）。
   バッジが「音声: 保存済み 300/300」になれば完了。両方の声を使うなら、声を切り替えてもう一度押す。
4. Safari の共有ボタン → 「ホーム画面に追加」。以後はホーム画面のアイコンから起動する。
5. 機内モードにして起動し、「テスト」で音が出ることを確認する（これが当日の確認手順そのもの）。

※ Safari は長期間使わないサイトのデータを消すことがあります。**大会の前日に一度ホーム画面から起動して**「保存済み」を確認してください。
※ iOS 16.4 以降は画面の常時点灯（Wake Lock）が使えます。それ以前、または「画面: 自動ロックを切ってください」と出る場合は、設定 → 画面表示と明るさ → 自動ロック → なし。

## Android での使い方

- 方法 A（同じ PWA）: 上と同じ手順を Chrome で行う。「ホーム画面に追加」も同様。
- 方法 B（1 ファイル版）: `start_announce_android.html` を Google ドライブ等でスマホに送り、Chrome で開く。
  音声が全部埋め込んであるので、保存操作は不要。

## 当日

- 自動ロックを「なし」に。画面が消えるとタイマーが止まります。
- 音量を最大に。スマホ単体では屋外で足りないので、Bluetooth スピーカーかメガホンの外部入力につなぐ。
- 「開始」を押すと、次の分から毎分流れます。「時報からの遅れ」で 00 秒から何秒遅らせて鳴らすかを選べます（標準 3 秒）。「停止」で止まります。
- 「デモ」にチェックすると、収録範囲外の時刻（夜など）でも同じ「分」の収録音声で動作確認ができます。当日は外してください。
- 「再生なし（表示のみ）」にチェックすると、画面のログだけで音を出しません。

## 音声を作り直す（時間帯・分数・声を変える）

PC に VOICEVOX（https://voicevox.hiroshiba.jp/）と ffmpeg を入れ、VOICEVOX を起動した状態で:

```
python tools/gen_clips.py --start 09:00 --end 12:30 --lead 3 --style 30 --out clips/no7
python tools/gen_clips.py --start 09:00 --end 12:30 --lead 3 --style 13 --out clips/ryusei
```

`--style` は VOICEVOX のスタイル ID（`curl http://127.0.0.1:50021/speakers` で一覧）。
声を追加・変更したときは `index.html` の `VOICES` 配列の id とラベルを合わせてください。

Android 用 1 ファイル版を作り直すときは:

```
python tools/build_android.py --pwa . --out start_announce_android.html --voice no7
```

## クレジット

音声合成: VOICEVOX（https://voicevox.hiroshiba.jp/）
使用キャラクター: VOICEVOX:No.7、VOICEVOX:青山龍星
各キャラクターの利用規約に従ってください（大会での使用は、クレジット表記があれば可）。
