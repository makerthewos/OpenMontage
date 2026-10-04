#!/usr/bin/env python3
"""把 TTS 音色匹配到**参考视频的声音风格**（音高 + 频谱包络）。

做法（全部可量化、可复现）：
  1. 两边都带限到同一带宽（默认 70–8000Hz）——否则比较不公平
  2. 用 Praat 测基频中位数、算能量门控后的频谱占比（低/中/存在感/齿音/质心）
  3. 音高用 **Praat PSOLA** 保共振峰变调（不是 ffmpeg asetrate，那个会连共振峰一起动）
  4. 频谱用 ffmpeg EQ 网格搜索逼近参考

⚠️ 关键教训：**基频必须在整片（或 ≥30s）上标定，不能用单句**。
同一音色换个句子，中位基频能从 98Hz 飘到 149Hz（语调起伏），
按单句算出来的变调倍数会把整片做塌（实测过一次，74Hz vs 目标 108Hz）。

用法：
    python scripts/match_voice_style.py --source my.wav --reference ref.wav --out matched.wav
    python scripts/match_voice_style.py --source my.wav --reference ref.wav --out m.wav --dry-run
"""
from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

BAND_HP, BAND_LP = 70, 8000


def sh(cmd):
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout


def bandlimit(src: Path, dst: Path) -> Path:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src),
                    "-af", f"highpass=f={BAND_HP},lowpass=f={BAND_LP}",
                    "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(dst)], check=True)
    return dst


def load(path: Path):
    w = wave.open(str(path))
    sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    if w.getnchannels() > 1:
        x = x.reshape(-1, w.getnchannels()).mean(1)
    return x, sr


def gated_profile(x, sr):
    """能量门控后的频谱占比：只统计有声帧，避免把静音/音乐算进去。"""
    n, hop = 2048, 1024
    F, rms = [], []
    for i in range(0, len(x) - n, hop):
        fr = x[i:i + n]
        rms.append(20 * np.log10(np.sqrt((fr ** 2).mean() + 1e-12) + 1e-9))
        F.append(fr * np.hanning(n))
    if not F:
        return {}
    rms = np.array(rms); F = np.array(F)
    S = np.abs(np.fft.rfft(F, axis=1))
    f = np.fft.rfftfreq(n, 1 / sr)
    S = S[rms >= np.percentile(rms, 60)]
    S = (S / (S.sum(1, keepdims=True) + 1e-9)).mean(0)
    return dict(low=float(S[(f >= 80) & (f < 350)].sum()),
                mid=float(S[(f >= 350) & (f < 2000)].sum()),
                pres=float(S[(f >= 2000) & (f < 5000)].sum()),
                sib=float(S[f >= 5000].sum()),
                centroid=float((S * f).sum()))


def f0_median(path: Path) -> float:
    import parselmouth
    p = parselmouth.Sound(str(path)).to_pitch(time_step=0.01, pitch_floor=60, pitch_ceiling=400)
    f = p.selected_array["frequency"]; f = f[f > 0]
    return float(np.median(f)) if len(f) else 0.0


def psola(src: Path, dst: Path, factor: float) -> Path:
    import parselmouth
    from parselmouth.praat import call
    snd = parselmouth.Sound(str(src))
    manip = call(snd, "To Manipulation", 0.01, 60.0, 400.0)
    tier = call(manip, "Extract pitch tier")
    call(tier, "Multiply frequencies", snd.xmin, snd.xmax, factor)
    call([tier, manip], "Replace pitch tier")
    call(manip, "Get resynthesis (overlap-add)").save(str(dst), "WAV")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="待匹配的旁白（TTS 输出）")
    ap.add_argument("--reference", required=True, help="参考视频的音轨")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true", help="只报告差距，不生成")
    ap.add_argument("--work", default="/tmp/match_voice")
    args = ap.parse_args()

    W = Path(args.work); W.mkdir(parents=True, exist_ok=True)
    src_b = bandlimit(Path(args.source), W / "src_band.wav")
    ref_b = bandlimit(Path(args.reference), W / "ref_band.wav")

    src_f0, ref_f0 = f0_median(src_b), f0_median(ref_b)
    src_p, ref_p = gated_profile(*load(src_b)), gated_profile(*load(ref_b))
    factor = ref_f0 / src_f0 if src_f0 else 1.0

    print(f"带宽统一到 {BAND_HP}–{BAND_LP} Hz")
    print(f"{'':10s} {'基频':>8s} {'低频':>8s} {'中频':>8s} {'存在感':>8s} {'齿音':>8s} {'质心':>9s}")
    for nm, f0, p in (("参考", ref_f0, ref_p), ("源", src_f0, src_p)):
        print(f"{nm:10s} {f0:7.0f}H {p['low']:7.1%} {p['mid']:7.1%} {p['pres']:7.1%} {p['sib']:7.1%} {p['centroid']:8.0f}H")
    print(f"\n需要变调 ×{factor:.4f}（{12 * np.log2(factor):+.1f} 半音）")

    if args.dry_run:
        return 0

    shifted = psola(src_b, W / "src_psola.wav", factor)
    print(f"PSOLA 后基频 {f0_median(shifted):.0f} Hz（目标 {ref_f0:.0f}）")

    best = None
    for e150, e300, e1000, e3500, e6500 in itertools.product(
            (0, 4, 8), (0, 4, 8), (0, 3, 6), (-2, -5), (-6, -12, -18)):
        af = (f"equalizer=f=150:t=q:w=0.9:g={e150},equalizer=f=300:t=q:w=1.0:g={e300},"
              f"equalizer=f=1000:t=q:w=1.5:g={e1000},equalizer=f=3500:t=q:w=1.2:g={e3500},"
              f"equalizer=f=6500:t=h:w=2500:g={e6500},loudnorm=I=-14:TP=-1.5:LRA=9")
        tmp = W / "grid.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(shifted), "-af", af,
                        "-ar", "24000", "-c:a", "pcm_s16le", str(tmp)], check=True)
        q = gated_profile(*load(tmp))
        err = sum(abs(q[k] - ref_p[k]) for k in ("low", "mid", "pres", "sib"))
        if best is None or err < best[0]:
            best = (err, dict(e150=e150, e300=e300, e1000=e1000, e3500=e3500, e6500=e6500), q, af)
    err, params, q, af = best
    print(f"\n最优 EQ {params}")
    print(f"{'匹配后':10s} {'':7s} {q['low']:7.1%} {q['mid']:7.1%} {q['pres']:7.1%} {q['sib']:7.1%} {q['centroid']:8.0f}H"
          f"   误差 {err:.3f}")

    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(shifted), "-af", af,
                    "-ar", "48000", "-c:a", "pcm_s16le", args.out], check=True)
    print(f"\n输出 {args.out}")
    print(f"滤镜链（EQ 部分）：{af}")
    json.dump(dict(source=args.source, reference=args.reference, pitch_factor=factor,
                   ref_f0=ref_f0, src_f0=src_f0, eq=params, error=err,
                   profile_after=q, profile_ref=ref_p),
              open(W / "match_report.json", "w"), ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
