#!/usr/bin/env python3
"""音色探测与标定：给一批音色 ID，自动判断"能不能用 / 走哪个 resource / 语速多少"。

从控制台拿到音色 ID（voice_type）后，直接跑这个：

    python scripts/probe_voice.py zh_male_qingcang_moon_bigtts zh_male_shenyeboke_moon_bigtts
    python scripts/probe_voice.py --compare zh_male_qingcang_moon_bigtts   # 与当前音色做 A/B

它做四件事：
  1. 逐个尝试已知的 resource_id，报告哪个组合可用（失败不计费）
  2. 标定语速（字/秒）——换音色必须重算，否则时长预算全错（见 F-24）
  3. --compare 时把新音色与当前音色拼成一条对比音频（带语音报幕）
  4. 输出可直接粘进 make_zi_lv_3min.py 的常量

成本：每个音色约 30 字符 × $0.000015 ≈ $0.0005。
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
sys.path.insert(0, str(REPO))

# 豆包按 resource 分组授权：不匹配就报 "resource ID is mismatched / not granted"
RESOURCE_CANDIDATES = [
    "seed-tts-2.0",                  # 语音合成 2.0（uranus / saturn / dipper 系列）
    "volc.service_type.10029",       # 大模型语音合成（moon 系列）
    "volc.service_type.10048",       # 其它大模型音色
    "volc.megatts.default",          # 声音复刻
]

TEST_TEXT = "意志力是消耗品，用完就没了。真正管用的是把门槛降到不可能失败。"
CURRENT_VOICE = "zh_male_ruyayichen_saturn_bigtts"


def sh(cmd: list[str]) -> str:
    r = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return r.stdout.strip()


def duration(path: Path) -> float:
    return float(sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(path)]) or 0)


def synth(tts, voice: str, resource: str, text: str, out: Path, rate: int = 0):
    for attempt in range(3):
        r = tts.execute({"text": text, "voice_id": voice, "resource_id": resource,
                         "format": "wav", "sample_rate": 24000, "speech_rate": rate,
                         "enable_timestamp": True, "return_usage": True,
                         "output_path": str(out)})
        if r.success:
            return r
        if "concurrency" in str(r.error):
            time.sleep(8)
            continue
        return r
    return r


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("voices", nargs="*", help="音色 ID（voice_type）")
    ap.add_argument("--compare", action="store_true", help="与当前音色拼 A/B 对比")
    ap.add_argument("--out", default="/tmp/voice_probe", help="输出目录")
    args = ap.parse_args()
    if not args.voices:
        sys.exit("用法：python scripts/probe_voice.py <音色ID> [更多…] [--compare]")

    from lib.env_loader import load_env
    load_env()
    from tools.tool_registry import registry
    registry.discover()
    tts = registry._tools["doubao_tts"]

    outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
    han = sum(1 for c in TEST_TEXT if "\u4e00" <= c <= "\u9fff")
    usable = []

    for voice in args.voices:
        done = False
        for res in RESOURCE_CANDIDATES:
            f = outdir / f"{voice}__{res.replace('.', '_')}.wav"
            r = synth(tts, voice, res, TEST_TEXT, f)
            if r.success:
                d = duration(f)
                rate = han / d if d else 0
                billed = int((r.data or {}).get("synthesize_text_length") or 0)
                print(f"✅ {voice}\n   resource={res}  时长 {d:.2f}s  语速 {rate:.2f} 字/秒  计费 {billed} 字符")
                usable.append((voice, res, d, rate))
                done = True
                break
            err = str(r.error)
            if "resource" in err or "mismatched" in err or "not granted" in err:
                continue                        # 换下一个 resource 再试
            print(f"❌ {voice}  resource={res}  {err[:90]}")
            done = True
            break
        if not done:
            print(f"❌ {voice}  所有 resource 都不可用 → 需要在控制台开通/认领该音色")
        time.sleep(2)

    if not usable:
        print("\n没有可用音色。请到控制台该音色页确认：① 是否已开通对应服务 ② 音色是否已认领")
        return 1

    print("\n=== 可直接粘进 make_zi_lv_3min.py ===")
    v, res, d, rate = usable[0]
    print(f'VOICE = "{v}"')
    print(f'# resource_id = "{res}"   基准语速 {rate:.2f} 字/秒')
    print(f"# 目标 180s 需语速 4.34 字/秒 → 建议 speech_rate ≈ "
          f"{max(0, round((4.34 / rate - 1) * 100))}")

    if args.compare:
        clips = []
        cur = outdir / "current.wav"
        if synth(tts, CURRENT_VOICE, "seed-tts-2.0", TEST_TEXT, cur).success:
            clips.append(("当前音色", cur))
        clips.append(("新音色", Path(outdir / f"{usable[0][0]}__{usable[0][1].replace('.', '_')}.wav")))
        parts, filt, labels = [], [], []
        idx = 0
        for name, path in clips:
            lab = outdir / f"lab_{idx}.aiff"
            subprocess.run(["say", "-v", "Tingting", name, "-o", str(lab)], check=False)
            for src in (lab, path):
                if not Path(src).exists():
                    continue
                parts += ["-i", str(src)]
                filt.append(f"[{idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo[a{idx}]")
                idx += 1
        if idx:
            fc = ";".join(filt) + ";" + "".join(f"[a{i}]" for i in range(idx)) + f"concat=n={idx}:v=0:a=1[out]"
            cmp_path = outdir / "音色对比.m4a"
            subprocess.run(["ffmpeg", "-v", "error", "-y", *parts, "-filter_complex", fc,
                            "-map", "[out]", "-c:a", "aac", "-b:a", "192k", str(cmp_path)], check=True)
            print(f"\n对比音频 → {cmp_path}（先报幕再播，顺序：当前 → 新）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
