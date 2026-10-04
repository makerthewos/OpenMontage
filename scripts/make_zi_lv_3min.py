#!/usr/bin/env python3
"""「自律」3 分钟版 · 黑底手绘风格（本地渲染 + 豆包配音）。

    python scripts/make_zi_lv_3min.py --stage audio   # 逐拍配音 + 实测时间轴
    python scripts/make_zi_lv_3min.py --stage render  # 出帧 + 合成
    python scripts/make_zi_lv_3min.py --stage all

成本：仅豆包配音按字符计费（$0.000015/字符）；渲染全部本地。
节拍表（唯一真源）：<PROJECT>/beat-sheet.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:                    # 让 tools/ 可导入
    sys.path.insert(0, str(REPO))

PROJECT = Path(os.environ.get(
    "ZI_LV_3MIN_DIR", Path.home() / "Desktop" / "视频生成素材" / "项目_自律_3分钟"))
BEAT_SHEET = PROJECT / "beat-sheet.yaml"
AUDIO = PROJECT / "audio"
ART = PROJECT / "artifacts"

VOICE = "zh_male_ruyayichen_saturn_bigtts"   # 男声·儒雅逸辰（账号可用）
TAIL_SILENCE = 0.6

# 按拍分配语速（speech_rate ≈ 提速百分比）。实测标定：男声儒雅逸辰
# rate 0 → 4.02 字/秒；20 → 1.20×；30 → 1.33×；40 → 1.44×。
# 关键情绪拍放慢、信息密集拍加快，既控总长又比"全片一个速度"更像真人。
RATE_SLOW, RATE_MID, RATE_FAST = 10, 18, 24
SLOW_BEATS = {"hook", "thesis", "turn", "turn2", "landing", "cta"}
FAST_BEATS = {"method1", "method2", "method3", "method4", "method5", "method6", "review", "setup"}


def speech_rate_for(beat_id: str) -> int:
    if beat_id in SLOW_BEATS:
        return RATE_SLOW
    if beat_id in FAST_BEATS:
        return RATE_FAST
    return RATE_MID


def sh(cmd: list[str]) -> str:
    r = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.stdout.strip()


def load_beats() -> tuple[dict, list[dict]]:
    import yaml
    d = yaml.safe_load(BEAT_SHEET.read_text(encoding="utf-8"))
    return d["meta"], d["beats"]


def duration(path: Path) -> float:
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(path)]) or 0)


# ── 阶段 5：配音 ───────────────────────────────────────────────────
def stage_audio(meta: dict, beats: list[dict]) -> dict:
    from tools.tool_registry import registry
    registry.discover()
    tts = registry._tools["doubao_tts"]
    AUDIO.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)

    pieces, silences, rows, cursor, billed = [], [], [], 0.0, 0
    for i, b in enumerate(beats, 1):
        rate = speech_rate_for(b["id"])
        wav = AUDIO / f"beat{i:02d}_{b['id']}_r{rate}.wav"
        if not wav.exists():                       # 断点续跑：已有就跳过（省钱）
            r = None
            for attempt in range(4):               # 并发限流时退避重试
                r = tts.execute({
                    "text": b["narration"], "voice_id": VOICE, "format": "wav",
                    "sample_rate": 24000, "speech_rate": rate,
                    "enable_timestamp": True, "return_usage": True,
                    "output_path": str(wav)})
                if r.success:
                    break
                print(f"   ⚠️ {b['id']} 第 {attempt+1} 次失败：{str(r.error)[:60]}")
                time.sleep(8)
            if not r or not r.success:
                raise SystemExit(f"配音失败：{b['id']}")
            billed += int((r.data or {}).get("synthesize_text_length") or 0)
            time.sleep(3)                          # 主动节流，避免撞并发上限
        d = duration(wav)
        pause = float(b.get("pause_before") or 0)
        rows.append(dict(id=b["id"], slot=b["slot"], name=b["name"], chars=b["chars"],
                         speech_rate=rate,
                         narration=b["narration"], pause_before=pause,
                         start=round(cursor + pause, 3),
                         end=round(cursor + pause + d, 3), audio=str(wav)))
        pieces.append(wav)
        silences.append(pause)
        cursor += pause + d
        print(f"  {b['id']:10s} rate={rate:2d}  {d:6.3f}s  累计 {cursor:7.2f}s")

    # 逐拍 + 停顿拼接成整条旁白
    narration = AUDIO / "narration.wav"
    parts, fc = [], []
    for i, (p, pause) in enumerate(zip(pieces, silences)):
        parts += ["-i", str(p)]
        if i:
            fc.append(f"[{i}:a]adelay={int(pause*1000)}|{int(pause*1000)}[a{i}]")
        else:
            fc.append(f"[{i}:a]anull[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(pieces))) + f"concat=n={len(pieces)}:v=0:a=1[cat]")
    fc.append(f"[cat]apad=pad_dur={TAIL_SILENCE}[out]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *parts, "-filter_complex", ";".join(fc),
                    "-map", "[out]", "-c:a", "pcm_s16le", str(narration)], check=True)

    total = duration(narration)
    timing = dict(engine=f"doubao:{VOICE}", narration_seconds=total,
                  billed_chars=billed, beats=rows)
    (ART / "narration_timing.json").write_text(
        json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n旁白 {total:.2f}s（目标 {meta['target_seconds']}s）· 计费 {billed} 字符 "
          f"≈ ${billed*0.000015:.5f}")
    return timing


# ── 阶段 6–7：出帧 + 合成 ──────────────────────────────────────────
def stage_render(meta: dict, timing: dict) -> None:
    from make_zi_lv_3min_screens import LINES, render_frames, render_bar_strips, assemble
    total = timing["narration_seconds"]
    rows = timing["beats"]
    screens = build_screen_timeline(rows, LINES, AUDIO)
    print(f"屏数 {len(screens)} / 成片 {total:.2f}s")
    render_frames(screens, total, PROJECT)
    render_bar_strips(total, PROJECT)
    assemble(screens, total, PROJECT, timing)
    out = PROJECT / "render" / "final.mp4"
    print(f"完成: {out}  {duration(out):.2f}s  {out.stat().st_size/1e6:.1f} MB")


CHAPTERS = {
    "hook": "01 误区", "context": "01 误区", "contrast": "01 误区", "thesis": "01 误区",
    "concept": "02 原理", "evidence": "02 原理", "deepen": "02 原理", "research": "02 原理",
    "turn": "02 原理", "principle": "02 原理",
    "method1": "03 方法", "setup": "03 方法", "method2": "03 方法", "method3": "03 方法",
    "method4": "03 方法", "method5": "03 方法", "method6": "03 方法", "review": "03 方法",
    "habit": "03 方法", "example": "03 方法",
    "identity": "04 认知", "compound": "04 认知", "counter": "04 认知", "mental": "04 认知",
    "turn2": "05 收束", "landing": "05 收束", "cta": "05 收束",
}


def build_screen_timeline(beats: list[dict], lines: list[tuple], audio_dir: Path) -> list[dict]:
    """按豆包**字级时间戳**把每拍的屏排到精确时刻（不是按字数估算）。"""
    import re
    han = re.compile(r"[\u4e00-\u9fff]")
    by_beat: dict[str, list] = {}
    for ln in lines:
        by_beat.setdefault(ln[0], []).append(ln)

    out: list[dict] = []
    for b in beats:
        group = by_beat.get(b["id"])
        if not group:
            raise SystemExit(f"节拍 {b['id']} 没有配屏")
        rate = b.get("speech_rate", 0)
        meta_path = audio_dir / f"beat{beats.index(b)+1:02d}_{b['id']}_r{rate}.wav.json"
        chars: list[tuple[str, float, float]] = []
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            for s in meta.get("data", {}).get("sentences", []):
                for w in s.get("words", []):
                    hs = han.findall(str(w.get("word", "")).strip())
                    if not hs:
                        continue
                    st = b["start"] + float(w["startTime"])
                    en = b["start"] + float(w["endTime"])
                    span = (en - st) / len(hs)
                    for k, ch in enumerate(hs):
                        chars.append((ch, st + k * span, st + (k + 1) * span))
        want = "".join(han.findall("".join(g[1] for g in group)))
        got = "".join(c[0] for c in chars)
        if got != want:                     # 时间戳缺失时退回按字数比例
            chars = []
            span = b["end"] - b["start"]
            weights = [max(1, len(han.findall(g[1]))) for g in group]
            tot = sum(weights)
            cur = b["start"]
            for g, w in zip(group, weights):
                d = span * w / tot
                out.append(dict(beat=b["id"], cn=g[1], key=g[2], color=g[3], motif=g[4],
                                layout=g[5], label=CHAPTERS.get(b["id"], ""),
                                start=round(cur, 3), end=round(cur + d, 3)))
                cur += d
            continue
        cur = 0
        for gi, g in enumerate(group):
            n = len(han.findall(g[1]))
            seg = chars[cur:cur + n]
            cur += n
            out.append(dict(beat=b["id"], cn=g[1], key=g[2], color=g[3], motif=g[4],
                            layout=g[5], label=CHAPTERS.get(b["id"], ""),
                            start=round(seg[0][1], 3), end=round(seg[-1][2], 3)))
    # 每屏显示到下一屏开始（最后一屏到片尾），保证不留空档
    for i, s in enumerate(out):
        s["end"] = out[i + 1]["start"] if i + 1 < len(out) else s["end"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["audio", "render", "all"], default="all")
    args = ap.parse_args()
    meta, beats = load_beats()
    timing_path = ART / "narration_timing.json"
    if args.stage in ("audio", "all"):
        timing = stage_audio(meta, beats)
    else:
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
    if args.stage in ("render", "all"):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        stage_render(meta, timing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
