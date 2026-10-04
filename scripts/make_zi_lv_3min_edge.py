#!/usr/bin/env python3
"""「自律」3 分钟版 · **Edge TTS 配音**（对照版本，音色可换）。

用途：把同一套画面配上另一种音色，用于 A/B 对比参考片的两种嗓音。
    python scripts/make_zi_lv_3min_edge.py --voice zh-CN-liaoning-XiaobeiNeural \\
        --reference <447074 的音轨> --out-suffix edge_xiaobei

⚠️ **edge-tts 不是商用授权音色**（见 F-19）。这一版只用于内部对比/非商用；
对外交付请用豆包/Azure/Qwen 等白名单引擎。

要点：
- 逐拍合成（整段语气不断），用 **WordBoundary** 事件拿字级时间戳
- 时间戳写成豆包同格式的 JSON，这样分屏对齐逻辑可以原样复用
- 换音色时长会变 → **必须重建分屏时间轴并重渲画面**（不能只换音轨）
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT = Path.home() / "Desktop" / "视频生成素材" / "项目_自律_3分钟"
HAN = re.compile(r"[\u4e00-\u9fff]")
TAIL_SILENCE = 0.6


def sh(cmd):
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout


def dur(p: Path) -> float:
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(p)]) or 0)


async def synth(text: str, voice: str, rate: str, mp3: Path):
    """返回 [(词, 起, 止)]，单位秒。boundary 必须显式指定 WordBoundary。"""
    import edge_tts
    c = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words, t0 = [], None
    with open(mp3, "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                if t0 is None:
                    t0 = time.time()
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                st = ch["offset"] / 1e7
                words.append((ch["text"], st, st + ch["duration"] / 1e7))
    return words


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="zh-CN-liaoning-XiaobeiNeural")
    ap.add_argument("--rate", default="+0%", help="edge 语速，如 +15%%")
    ap.add_argument("--out-suffix", default="edge")
    ap.add_argument("--reference", default="", help="要匹配音色的参考音轨（可选）")
    ap.add_argument("--no-match", action="store_true", help="不做音色匹配")
    args = ap.parse_args()

    import yaml
    sheet = yaml.safe_load((PROJECT / "beat-sheet.yaml").read_text(encoding="utf-8"))
    beats = sheet["beats"]

    tag = args.out_suffix
    base = PROJECT / f"v_{tag}"
    audio = base / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    (base / "artifacts").mkdir(exist_ok=True)

    rows, pieces, pauses, cursor = [], [], [], 0.0
    for i, b in enumerate(beats, 1):
        rate_key = 0                       # 用 0 占位，文件名只求稳定
        wav = audio / f"beat{i:02d}_{b['id']}_r{rate_key}.wav"
        meta_path = wav.with_suffix(".wav.json")
        if not wav.exists():
            mp3 = audio / f"beat{i:02d}_{b['id']}.mp3"
            words = asyncio.run(synth(b["narration"], args.voice, args.rate, mp3))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mp3),
                            "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(wav)], check=True)
            # 写成豆包同格式，让分屏对齐逻辑原样复用
            meta_path.write_text(json.dumps({"data": {"sentences": [{"words": [
                {"word": w, "startTime": st, "endTime": en} for w, st, en in words]}]}},
                ensure_ascii=False), encoding="utf-8")
        d = dur(wav)
        pause = float(b.get("pause_before") or 0)
        rows.append(dict(id=b["id"], slot=b["slot"], name=b["name"], chars=b["chars"],
                         speech_rate=rate_key, pause_before=pause,
                         start=round(cursor + pause, 3), end=round(cursor + pause + d, 3),
                         audio=str(wav)))
        pieces.append(wav); pauses.append(pause)
        cursor += pause + d
        print(f"  {b['id']:10s} {d:6.3f}s  累计 {cursor:7.2f}s")

    # 拼接（保留非均匀停顿）
    out_raw = audio / "narration_raw.wav"
    parts, fc = [], []
    for i, (p, pause) in enumerate(zip(pieces, pauses)):
        parts += ["-i", str(p)]
        if i:
            fc.append(f"[{i}:a]adelay={int(pause*1000)}|{int(pause*1000)}[a{i}]")
        else:
            fc.append(f"[{i}:a]anull[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(pieces))) + f"concat=n={len(pieces)}:v=0:a=1[cat]")
    fc.append(f"[cat]apad=pad_dur={TAIL_SILENCE}[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *parts, "-filter_complex", ";".join(fc),
                    "-map", "[out]", "-c:a", "pcm_s16le", str(out_raw)], check=True)

    total = dur(out_raw)
    narration = audio / "narration.wav"
    match_info = {}
    if args.reference and not args.no_match:
        print("\n音色匹配到参考片 …")
        r = subprocess.run([sys.executable, str(Path(__file__).parent / "match_voice_style.py"),
                            "--source", str(out_raw), "--reference", args.reference,
                            "--out", str(narration), "--work", str(base / "match")],
                           text=True, capture_output=True)
        print(r.stdout[-1200:])
        if r.returncode != 0 or not narration.exists():
            print("匹配失败，退回原始音轨")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out_raw),
                            "-c:a", "pcm_s16le", str(narration)], check=True)
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out_raw),
                        "-c:a", "pcm_s16le", str(narration)], check=True)

    # 响度精确归一（单遍 loudnorm 落点不准，补一次音量校正）
    # ⚠️ ebur128 会先逐秒打印读数，最后才给 Summary；必须取**最后一条**，
    # 否则拿到的是 t≈0.1s 的瞬时值（约 -70），会补出一个 +56dB 的离谱增益。
    meters = re.findall(r"I:\s+(-?\d+\.\d+) LUFS",
                        sh(["ffmpeg", "-hide_banner", "-i", str(narration), "-af", "ebur128", "-f", "null", "-"]))
    if meters:
        delta = -14.0 - float(meters[-1])
        if abs(delta) > 0.3:
            fixed = audio / "narration_norm.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(narration),
                            "-af", f"volume={delta:.2f}dB,alimiter=limit=0.84",
                            "-ar", "48000", "-c:a", "pcm_s16le", str(fixed)], check=True)
            fixed.replace(narration)
            print(f"响度校正 {delta:+.2f} dB")

    timing = dict(engine=f"edge:{args.voice}@{args.rate}", narration_seconds=dur(narration),
                  billed_chars=0, beats=rows)
    (base / "artifacts" / "narration_timing.json").write_text(
        json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n旁白 {timing['narration_seconds']:.2f}s（{len(beats)} 拍）→ {narration}")
    print(f"下一步渲染：--render 时会重建分屏时间轴（时长变了必须重渲画面）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
