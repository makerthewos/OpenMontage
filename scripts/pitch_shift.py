#!/usr/bin/env python3
"""用 Praat（PSOLA）做**保共振峰**变调：只改音高，不改音色。

为什么不用 ffmpeg 的 asetrate：那是"整体重采样"，音高和共振峰一起动，
降多了会发闷、像换了个人。PSOLA 重合成只改基频轨迹，共振峰保留，
所以"把 149Hz 的男声压到 108Hz"这种大跨度变调才听得出是同一个人的低音版。

用法：
    python scripts/pitch_shift.py in.wav out.wav --semitones -5.5
    python scripts/pitch_shift.py in.wav out.wav --factor 0.725   # 108/149
    python scripts/pitch_shift.py in.wav out.wav --to-hz 108 --from-hz 149
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def pitch_shift(src: Path, dst: Path, factor: float,
                pitch_floor: float = 60.0, pitch_ceiling: float = 400.0) -> Path:
    import parselmouth
    from parselmouth.praat import call

    snd = parselmouth.Sound(str(src))
    manip = call(snd, "To Manipulation", 0.01, pitch_floor, pitch_ceiling)
    tier = call(manip, "Extract pitch tier")
    call(tier, "Multiply frequencies", snd.xmin, snd.xmax, factor)
    call([tier, manip], "Replace pitch tier")
    out = call(manip, "Get resynthesis (overlap-add)")
    out.save(str(dst), "WAV")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser(description="保共振峰变调（Praat PSOLA）")
    ap.add_argument("src"); ap.add_argument("dst")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--semitones", type=float, help="变调半音数，负数=降调")
    g.add_argument("--factor", type=float, help="频率倍率，如 0.725")
    g.add_argument("--to-hz", type=float, help="目标基频（需配 --from-hz）")
    ap.add_argument("--from-hz", type=float, help="当前基频（配 --to-hz）")
    args = ap.parse_args()

    if args.semitones is not None:
        factor = 2 ** (args.semitones / 12)
    elif args.factor is not None:
        factor = args.factor
    else:
        if not args.from_hz:
            sys.exit("--to-hz 需要同时给 --from-hz")
        factor = args.to_hz / args.from_hz

    src, dst = Path(args.src), Path(args.dst)
    pitch_shift(src, dst, factor)
    print(f"{src.name} → {dst.name}   变调 ×{factor:.4f}"
          f"（{12 * (factor and __import__('math').log2(factor)):+.1f} 半音）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
