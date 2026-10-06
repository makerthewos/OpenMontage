#!/usr/bin/env python3
"""整段合成版：从「一次性合成」的字级时间戳重建分屏时间轴并渲染。

与逐拍版的区别（也是自然度的来源）：
  - 一次合成整篇 → 引擎按标点自然停顿，**数字静音 0%**（逐拍版 10.7%）
  - 无 27 处人工硬切静音，语气不被打断
  - 时间轴按字级时间戳对齐（不是按字数估算）

用法：python render_whole.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path("/Users/makerthewos/Desktop/OpenMontage")
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

import make_zi_lv_3min_screens as S            # noqa: E402
from make_zi_lv_3min import CHAPTERS           # noqa: E402

PROJ = Path("/Users/makerthewos/Desktop/视频生成素材/项目_自律_3分钟")
WHOLE = Path("/tmp/voice/whole_r12.wav")
META = Path("/tmp/voice/whole_r12.wav.json")
OUT = PROJ / "v_whole"
HAN = re.compile(r"[\u4e00-\u9fff]")

CHAIN = ("highpass=f=70,lowpass=f=9000,"
         "equalizer=f=250:t=q:w=1.0:g=1.5,equalizer=f=3200:t=q:w=1.0:g=2,"
         "acompressor=threshold=-20dB:ratio=2.2:attack=12:release=140:makeup=1,"
         "loudnorm=I=-14:TP=-1.5:LRA=10")


def main() -> int:
    import yaml
    beats = yaml.safe_load((PROJ / "beat-sheet.yaml").read_text(encoding="utf-8"))["beats"]

    # 全局字级时间戳
    meta = json.loads(META.read_text(encoding="utf-8"))["data"]
    chars = []
    for s in meta.get("sentences", []):
        for w in s.get("words", []):
            hs = HAN.findall(str(w.get("word", "")).strip())
            if not hs:
                continue
            st, en = float(w["startTime"]), float(w["endTime"])
            span = (en - st) / len(hs)
            for k, ch in enumerate(hs):
                chars.append((ch, st + k * span, st + (k + 1) * span))

    want = "".join("".join(HAN.findall(b["narration"])) for b in beats)
    got = "".join(c[0] for c in chars)
    assert want == got, f"文案与配音不匹配（{len(want)} vs {len(got)} 字）"
    print(f"字级对齐 ✓ {len(chars)} 字")

    # 按拍 → 按屏 切分
    by_beat: dict[str, list] = {}
    for ln in S.LINES:
        by_beat.setdefault(ln[0], []).append(ln)

    screens, cur = [], 0
    for b in beats:
        group = by_beat[b["id"]]
        for gi, g in enumerate(group):
            n = len(HAN.findall(g[1]))
            seg = chars[cur:cur + n]
            cur += n
            screens.append(dict(beat=b["id"], cn=g[1], key=g[2], color=g[3], motif=g[4],
                                layout=g[5], label=CHAPTERS.get(b["id"], ""),
                                start=round(seg[0][1], 3), end=round(seg[-1][2], 3)))
    for i, s in enumerate(screens):
        s["end"] = screens[i + 1]["start"] if i + 1 < len(screens) else s["end"]
    print(f"分屏 {len(screens)} 屏 / 末屏结束 {screens[-1]['end']:.2f}s")

    # 后处理（自然优先链）
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "audio").mkdir(exist_ok=True)
    nar = OUT / "audio" / "narration.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(WHOLE), "-af", CHAIN,
                    "-ar", "48000", "-c:a", "pcm_s16le", str(nar)], check=True)
    # 响度精确校准（单遍 loudnorm 落点不准）
    meters = re.findall(r"I:\s+(-?\d+\.\d+) LUFS",
                        subprocess.run(["ffmpeg", "-hide_banner", "-i", str(nar), "-af", "ebur128",
                                        "-f", "null", "-"], text=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout)
    if meters:
        delta = -14.0 - float(meters[-1])
        if abs(delta) > 0.3:
            fixed = OUT / "audio" / "narration_norm.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(nar),
                            "-af", f"volume={delta:.2f}dB,alimiter=limit=0.84",
                            "-ar", "48000", "-c:a", "pcm_s16le", str(fixed)], check=True)
            fixed.replace(nar)
            print(f"响度校正 {delta:+.2f} dB")

    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", str(nar)], capture_output=True, text=True).stdout)
    timing = dict(engine="doubao:zh_male_ruyayichen_saturn_bigtts@12(整段)",
                  narration_seconds=dur, billed_chars=801, beats=[])
    (OUT / "artifacts").mkdir(exist_ok=True)
    (OUT / "artifacts" / "narration_timing.json").write_text(
        json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    json.dump(screens, open(OUT / "artifacts" / "screens.json", "w"), ensure_ascii=False, indent=2)

    print(f"旁白 {dur:.2f}s → 开始渲染")
    S.render_frames(screens, dur, OUT)
    S.render_bar_strips(dur, OUT)
    S.assemble(screens, dur, OUT, timing)
    f = OUT / "render" / "final.mp4"
    print(f"完成: {f}  {f.stat().st_size/1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
