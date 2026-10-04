#!/usr/bin/env python3
"""「自律」20 秒 · 黑底手绘风格成片 v2（本地渲染，无付费 API）。

    python scripts/make_black_lineart_20s.py --frames   # 出样张
    python scripts/make_black_lineart_20s.py            # 出全部帧 + 合成

源素材（配音与字级时间戳）取自 projects/zi-lv-20s；可用环境变量覆盖：
    BLACK_LINEART_SRC  BLACK_LINEART_OUT

v2 改动（对应反馈）：
  2. 素材更丰富：火柴人（站/走/爬/推）+ 更细的线稿母题 + 手绘装饰（圈画、箭头、排线）
                 + 关键词彩色强调（白/金/蓝）+ 版式在 3 种之间轮换
  3. 底部内容进度条（逐帧渲染，随时间增长）
  4. 字幕缩小（68→54）并上移到进度条上方

风格来源：docs/04-style-profile-black-lineart.md
成本：本脚本零 API 调用（配音见 COSTS.md）。

Run:
    python build.py --frames   # 只出前三屏样张
    python build.py            # 出全部帧 + 合成
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent          # OpenMontage checkout
ROOT = Path(os.environ.get("BLACK_LINEART_OUT", REPO / "projects" / "black-lineart-20s"))
WORK = ROOT / "work"
FRAMES = WORK / "frames"
RENDER = ROOT / "render"
SRC = Path(os.environ.get("BLACK_LINEART_SRC", REPO / "projects" / "zi-lv-20s"))

W, H, FPS = 1080, 1920, 30
BG = (7, 5, 3)
WHITE = (240, 240, 240)
GOLD = (232, 200, 122)
BLUE = (122, 176, 255)
DIM = (130, 126, 120)
TRACK = (38, 35, 32)

FONT_HAND = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/a3c69464b629577766c23bcdb12ffbfe3759b923.asset/AssetData/Hanzipen.ttc"
FONT_PING = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"
IDX_SC_SEMIBOLD = 11

SUB_Y, SUB_SIZE = 1740, 54          # 字幕：缩小 + 上移
BAR_X, BAR_Y, BAR_W, BAR_H = 60, 1852, 960, 10   # 进度条（底部）

# (台词, 关键词, 关键词色, 母题, 版式, 章节标)
LINES = [
    ("自律从来不是",      "自律",      WHITE, "calendar",  "key_top", "01 钩子"),
    ("靠意志力撑出来的",   "意志力",    WHITE, "battery",   "key_top", "01 钩子"),
    ("意志力是消耗品",     "消耗品",    BLUE,  "battery",   "art_top", "02 拆解"),
    ("用完就没了",        "会耗尽",    BLUE,  "drained",   "art_top", "02 拆解"),
    ("真正管用的是",      "换个思路",   BLUE,  "idea",      "key_top", "02 拆解"),
    ("把门槛降到不可能失败", "门槛",     WHITE, "stairs_dn", "key_top", "02 拆解"),
    ("想跑步先穿上鞋",     "先穿上鞋",   WHITE, "shoe",      "art_top", "02 拆解"),
    ("想读书先翻开一页",   "翻开一页",   WHITE, "book",      "art_top", "02 拆解"),
    ("今晚挑一件小事",     "一件小事",   BLUE,  "checklist", "key_top", "03 落点"),
    ("把第一步拆到",      "第一步",    WHITE, "stairs_up", "key_top", "03 落点"),
    ("三分钟能做完",      "3 分钟",    BLUE,  "timer",     "art_top", "03 落点"),
]


# ── 手绘线条基础 ───────────────────────────────────────────────────
def wobble(p0, p1, n=26, amp=2.6, seed=0):
    rng = random.Random(seed)
    (x0, y0), (x1, y1) = p0, p1
    pts = []
    for i in range(n + 1):
        t = i / n
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        if 0 < i < n:
            x += rng.uniform(-amp, amp)
            y += rng.uniform(-amp, amp)
        pts.append((x, y))
    return pts


def poly(d, pts, width=6, fill=WHITE):
    d.line(pts, fill=fill, width=width, joint="curve")


def seg(d, p0, p1, seed=0, width=6, fill=WHITE, amp=2.4):
    poly(d, wobble(p0, p1, max(6, int(((p1[0]-p0[0])**2 + (p1[1]-p0[1])**2) ** .5 / 14)), amp, seed), width, fill)


def rect(d, box, seed=0, width=6, fill=WHITE, r=12):
    x0, y0, x1, y1 = box
    seg(d, (x0 + r, y0), (x1 - r, y0), seed, width, fill)
    seg(d, (x1, y0 + r), (x1, y1 - r), seed + 1, width, fill)
    seg(d, (x1 - r, y1), (x0 + r, y1), seed + 2, width, fill)
    seg(d, (x0, y1 - r), (x0, y0 + r), seed + 3, width, fill)


def circle(d, cx, cy, r, seed=0, width=6, fill=WHITE):
    pts = []
    rng = random.Random(seed)
    for i in range(29):
        a = 2 * 3.14159 * i / 28
        rr = r + rng.uniform(-2.5, 2.5)
        pts.append((cx + rr * __import__("math").cos(a), cy + rr * __import__("math").sin(a)))
    d.line(pts, fill=fill, width=width, joint="curve")


def hatch(d, x, y, n=3, seed=0, fill=DIM, width=4):
    """排线阴影（手绘感）。"""
    for i in range(n):
        seg(d, (x + i * 16, y), (x + i * 16 - 12, y + 22), seed + i, width, fill, 1.6)


# ── 火柴人 ─────────────────────────────────────────────────────────
def stick(d, x, y, h=150, pose="stand", seed=0, fill=WHITE, width=6):
    """火柴人：head + 躯干 + 四肢。pose: stand/walk/climb/push/sit"""
    hr = h * 0.13
    circle(d, x, y - h + hr, hr, seed, width, fill)
    hip = (x, y - h * 0.45)
    seg(d, (x, y - h + 2 * hr), hip, seed + 1, width, fill)
    if pose == "stand":
        seg(d, (x, hip[1]), (x - h * 0.22, y), seed + 2, width, fill)
        seg(d, (x, hip[1]), (x + h * 0.22, y), seed + 3, width, fill)
        seg(d, (x, y - h * 0.78), (x - h * 0.3, y - h * 0.55), seed + 4, width, fill)
        seg(d, (x, y - h * 0.78), (x + h * 0.3, y - h * 0.55), seed + 5, width, fill)
    elif pose == "walk":
        seg(d, (x, hip[1]), (x - h * 0.34, y), seed + 2, width, fill)
        seg(d, (x, hip[1]), (x + h * 0.3, y - h * 0.12), seed + 3, width, fill)
        seg(d, (x, y - h * 0.78), (x - h * 0.34, y - h * 0.6), seed + 4, width, fill)
        seg(d, (x, y - h * 0.78), (x + h * 0.34, y - h * 0.62), seed + 5, width, fill)
    elif pose == "climb":
        seg(d, (x, hip[1]), (x - h * 0.3, y - h * 0.2), seed + 2, width, fill)
        seg(d, (x, hip[1]), (x + h * 0.24, y), seed + 3, width, fill)
        seg(d, (x, y - h * 0.78), (x - h * 0.34, y - h * 0.95), seed + 4, width, fill)
        seg(d, (x, y - h * 0.78), (x + h * 0.3, y - h * 0.6), seed + 5, width, fill)
    elif pose == "push":
        seg(d, (x, hip[1]), (x - h * 0.3, y), seed + 2, width, fill)
        seg(d, (x, hip[1]), (x + h * 0.26, y), seed + 3, width, fill)
        seg(d, (x, y - h * 0.78), (x + h * 0.5, y - h * 0.8), seed + 4, width, fill)
        seg(d, (x, y - h * 0.78), (x + h * 0.48, y - h * 0.66), seed + 5, width, fill)
    elif pose == "sit":
        seg(d, (x, hip[1]), (x + h * 0.34, hip[1]), seed + 2, width, fill)
        seg(d, (x + h * 0.34, hip[1]), (x + h * 0.34, y), seed + 3, width, fill)
        seg(d, (x, y - h * 0.78), (x + h * 0.28, y - h * 0.62), seed + 4, width, fill)


# ── 母题 ───────────────────────────────────────────────────────────
def motif(d, kind, cx, cy, seed=0):
    if kind == "calendar":                                # 自律：一周打卡格
        for r in range(2):
            for c in range(4):
                box = (cx - 208 + c * 112, cy - 84 + r * 112, cx - 124 + c * 112, cy + 6 + r * 112)
                rect(d, box, seed + r * 4 + c, 5)
                if (r * 4 + c) < 5:
                    seg(d, (box[0] + 14, box[1] + 50), (box[0] + 34, box[1] + 74), seed + 20 + c, 6)
                    seg(d, (box[0] + 34, box[1] + 74), (box[0] + 70, box[1] + 20), seed + 21 + c, 6)
    elif kind == "battery":                               # 意志力：电池 + 电量格
        rect(d, (cx - 170, cy - 80, cx + 130, cy + 80), seed)
        seg(d, (cx + 130, cy - 30), (cx + 165, cy - 30), seed, 9)
        seg(d, (cx + 165, cy - 30), (cx + 165, cy + 30), seed, 9)
        seg(d, (cx + 130, cy + 30), (cx + 165, cy + 30), seed, 9)
        for i in range(3):
            x = cx - 140 + i * 88
            rect(d, (x, cy - 52, x + 66, cy + 52), seed + 10 + i, 5, r=6)
    elif kind == "drained":                               # 会耗尽：空格子 + 火花
        rect(d, (cx - 170, cy - 80, cx + 130, cy + 80), seed)
        d.line(wobble((cx - 140, cy - 52), (cx + 100, cy + 52), 20, 2.5, seed + 1), fill=DIM, width=5)
        for i in range(4):                                 # 小火花
            a = -0.6 + i * 0.4
            px, py = cx + 190 * __import__("math").cos(a), cy + 110 * __import__("math").sin(a)
            seg(d, (px, py), (px + 22, py - 12), seed + 30 + i, 5)
            seg(d, (px, py), (px + 4, py - 26), seed + 40 + i, 5)
    elif kind == "idea":                                  # 换个思路：灯泡 + 环绕箭头
        circle(d, cx, cy - 20, 66, seed, 6)
        seg(d, (cx, cy - 20), (cx, cy + 26), seed + 1, 6)
        seg(d, (cx - 26, cy + 46), (cx + 26, cy + 46), seed + 2, 6)
        seg(d, (cx - 20, cy + 66), (cx + 20, cy + 66), seed + 3, 6)
        for i in range(3):
            a0 = -2.4 + i * 0.5
            px = cx + 200 * __import__("math").cos(a0)
            py = cy + 40 + 200 * __import__("math").sin(a0)
            seg(d, (px, py), (px + 26, py + 8), seed + 50 + i, 5, DIM)
    elif kind == "stairs_dn":                             # 门槛：下行台阶 + 火柴人下行
        x, y = cx - 230, cy - 110
        for i in range(4):
            seg(d, (x, y), (x + 96, y), seed + i, 6)
            seg(d, (x + 96, y), (x + 96, y + 56), seed + i, 6)
            x, y = x + 96, y + 56
        seg(d, (x, y), (x + 96, y), seed + 9, 6)
        stick(d, cx + 40, cy + 116, 130, "walk", seed + 60)
        seg(d, (cx - 250, cy - 150), (cx + 250, cy - 150), seed + 70, 4, DIM)
    elif kind == "stairs_up":                             # 第一步：上行台阶 + 火柴人爬
        x, y = cx - 150, cy + 120
        for i in range(3):
            seg(d, (x, y), (x + 82, y), seed + i, 6)
            seg(d, (x + 82, y), (x + 82, y - 62), seed + i, 6)
            x, y = x + 82, y - 62
        seg(d, (x, y), (x + 82, y), seed + 9, 6)
        stick(d, cx + 96, cy + 122, 140, "climb", seed + 60)
    elif kind == "shoe":                                  # 先穿上鞋：跑鞋 + 速度线
        seg(d, (cx - 190, cy + 60), (cx - 190, cy - 6), seed, 6)
        seg(d, (cx - 190, cy - 6), (cx - 60, cy - 40), seed, 6)
        seg(d, (cx - 60, cy - 40), (cx + 80, cy + 6), seed, 6)
        seg(d, (cx + 80, cy + 6), (cx + 190, cy + 10), seed, 6)
        seg(d, (cx - 190, cy + 60), (cx + 190, cy + 64), seed + 1, 7)
        for i in range(3):                                 # 鞋带
            seg(d, (cx - 90, cy - 32 + i * 16), (cx - 30, cy - 14 + i * 16), seed + 10 + i, 4)
        for i in range(3):                                 # 速度线
            seg(d, (cx - 250 + i * 10, cy - 40 + i * 34), (cx - 160 + i * 10, cy - 40 + i * 34), seed + 20 + i, 4, DIM)
    elif kind == "book":                                  # 翻开一页：摊开的书 + 翻页箭头
        seg(d, (cx, cy - 70), (cx, cy + 76), seed, 6)
        seg(d, (cx, cy - 70), (cx - 180, cy - 36), seed + 1, 6)
        seg(d, (cx - 180, cy - 36), (cx - 170, cy + 88), seed + 2, 6)
        seg(d, (cx - 170, cy + 88), (cx, cy + 76), seed + 3, 6)
        seg(d, (cx, cy - 70), (cx + 180, cy - 36), seed + 4, 6)
        seg(d, (cx + 180, cy - 36), (cx + 170, cy + 88), seed + 5, 6)
        seg(d, (cx + 170, cy + 88), (cx, cy + 76), seed + 6, 6)
        for i in range(3):
            seg(d, (cx - 150, cy - 10 + i * 26), (cx - 30, cy - 4 + i * 26), seed + 10 + i, 4, DIM)
        seg(d, (cx + 40, cy - 30), (cx + 150, cy - 60), seed + 20, 5, GOLD)   # 翻页箭头
        seg(d, (cx + 150, cy - 60), (cx + 118, cy - 46), seed + 21, 5, GOLD)
    elif kind == "checklist":                             # 一件小事：清单 + 只勾一项
        for i in range(3):
            y = cy - 76 + i * 76
            box = (cx - 190, y - 24, cx - 146, y + 20)
            rect(d, box, seed + i, 5, r=6)
            seg(d, (cx - 110, y), (cx + 90 - i * 30, y), seed + 10 + i, 5, WHITE if i == 0 else DIM)
        seg(d, (cx - 184, cy - 4), (cx - 168, cy + 14), seed + 30, 6, GOLD)
        seg(d, (cx - 168, cy + 14), (cx - 140, cy - 20), seed + 31, 6, GOLD)
        seg(d, (cx - 190, cy + 96), (cx + 150, cy + 96), seed + 40, 4, DIM)
        stick(d, cx + 40, cy + 90, 120, "sit", seed + 50, DIM, 5)
    elif kind == "timer":                                 # 3 分钟：秒表 + 刻度
        circle(d, cx, cy, 118, seed, 7)
        for i in range(12):                               # 刻度
            a = 2 * 3.14159 * i / 12
            px, py = cx + 100 * __import__("math").cos(a), cy + 100 * __import__("math").sin(a)
            seg(d, (px, py), (px + 14 * __import__("math").cos(a), py + 14 * __import__("math").sin(a)),
                seed + i, 5, DIM if i % 3 else WHITE)
        seg(d, (cx, cy), (cx, cy - 74), seed + 30, 7)
        seg(d, (cx, cy), (cx + 54, cy + 30), seed + 31, 7, GOLD)
        seg(d, (cx - 40, cy - 140), (cx + 40, cy - 140), seed + 32, 8)
        seg(d, (cx, cy - 140), (cx, cy - 118), seed + 33, 8)


# ── 一屏的底图 ─────────────────────────────────────────────────────
def render_base(idx, cn, key, key_color, kind, layout, label) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_lab = ImageFont.truetype(FONT_PING, 38, index=IDX_SC_SEMIBOLD)
    d.text((66, 92), label, font=f_lab, fill=DIM)
    d.text((W - 66, 92), f"{idx+1:02d}/{len(LINES)}", font=f_lab, fill=DIM, anchor="ra")

    key_y, art_y = (int(H * 0.40), int(H * 0.645)) if layout == "key_top" else (int(H * 0.685), int(H * 0.365))

    # 关键词（手写体，可彩色强调）
    size = 190
    f_key = ImageFont.truetype(FONT_HAND, size)
    while f_key.getlength(key) > W - 240 and size > 60:
        size -= 8
        f_key = ImageFont.truetype(FONT_HAND, size)
    d.text((W // 2, key_y), key, font=f_key, fill=key_color, anchor="mm")

    # 关键词下的手绘装饰：下划线 or 圈画
    if idx % 3 == 0:
        seg(d, (W // 2 - 150, key_y + size * 0.62), (W // 2 + 150, key_y + size * 0.62), idx, 6, key_color, 3.2)
    elif idx % 3 == 1:
        circle(d, W // 2, key_y, max(f_key.getlength(key) / 2 + 26, 90), idx + 5, 5, key_color)

    # 母题画在透明层后整体缩放，保持"画得小、放得大"的一致观感
    layer = Image.new("RGBA", (900, 620), (0, 0, 0, 0))
    motif(ImageDraw.Draw(layer), kind, 450, 310, seed=idx * 17 + 3)
    scale = 1.12
    layer = layer.resize((int(900 * scale), int(620 * scale)), Image.LANCZOS)
    img.paste(layer, (W // 2 - layer.width // 2, art_y - layer.height // 2), layer)

    # 底部渐隐 + 字幕 + 进度条轨道（进度条填充逐帧画）
    grad = Image.new("L", (1, 260))
    for i in range(260):
        grad.putpixel((0, i), int(150 * (i / 260) ** 1.6))
    img.paste(Image.new("RGB", (W, 260), (0, 0, 0)), (0, H - 260),
              grad.resize((W, 260)))
    d = ImageDraw.Draw(img)
    f_sub = ImageFont.truetype(FONT_PING, SUB_SIZE, index=IDX_SC_SEMIBOLD)
    d.text((W // 2, SUB_Y), cn, font=f_sub, fill=GOLD, anchor="mm")
    d.rounded_rectangle((BAR_X, BAR_Y, BAR_X + BAR_W, BAR_Y + BAR_H), BAR_H // 2, fill=TRACK)
    return img


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", action="store_true", help="只出前三屏样张")
    ap.add_argument("--fps", type=int, default=FPS)
    args = ap.parse_args()
    for p in (WORK, FRAMES, RENDER):
        p.mkdir(exist_ok=True)

    timeline = build_timeline()
    total = 20.561
    print(f"时间轴 {len(timeline)} 屏 / 成片 {total}s")

    if args.frames:
        for ln in timeline[:3]:
            img = render_base(ln["idx"], ln["cn"], ln["key"], ln["color"], ln["motif"], ln["layout"], ln["label"])
            img.save(WORK / f"sample{ln['idx']}.png")
        print("样张 →", WORK / "sample0.png 等")
        return 0

    # 逐帧：底图缓存 + 画进度条
    for f in FRAMES.glob("*.png"):
        f.unlink()
    n_frames = int(total * args.fps)
    bases = {ln["idx"]: render_base(ln["idx"], ln["cn"], ln["key"], ln["color"],
                                    ln["motif"], ln["layout"], ln["label"]) for ln in timeline}
    for i in range(n_frames):
        t = i / args.fps
        cur = timeline[0]
        for ln in timeline:
            if t >= ln["start"] - 1e-6:
                cur = ln
        img = bases[cur["idx"]].copy()
        d = ImageDraw.Draw(img)
        prog = min(1.0, t / total)
        w = int(BAR_W * prog)
        if w > 0:
            d.rounded_rectangle((BAR_X, BAR_Y, BAR_X + w, BAR_Y + BAR_H), BAR_H // 2, fill=GOLD)
        img.save(FRAMES / f"{i:05d}.png")
    print(f"出帧完成 {n_frames} 帧")

    out = RENDER / "final.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-framerate", str(args.fps), "-i", str(FRAMES / "%05d.png"),
        "-i", str(SRC / "assets/audio/narration.wav"),
        "-filter_complex",
        f"[0:v]fade=t=in:st=0:d=0.3,fade=t=out:st={total - 0.6:.3f}:d=0.6,format=yuv420p[v];"
        f"[1:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
        f"loudnorm=I=-14:TP=-1.5:LRA=9[a]",
        "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "17",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
    print(f"完成: {out}  {float(dur):.2f}s  {out.stat().st_size/1e6:.1f} MB")
    return 0


def build_timeline():
    import re
    han = re.compile(r"[\u4e00-\u9fff]")
    timing = json.load(open(SRC / "artifacts" / "narration_timing.json"))
    offset = {b["id"]: b["start"] for b in timing["beats"]}
    chars = []
    for i, bid in enumerate([b["id"] for b in timing["beats"]], 1):
        meta = json.load(open(SRC / f"assets/audio/_beat_{i}.wav.json"))
        for s in meta["data"]["sentences"]:
            for w in s["words"]:
                st = offset[bid] + float(w["startTime"])
                en = offset[bid] + float(w["endTime"])
                hs = han.findall(w["word"].strip())
                if not hs:
                    continue
                span = (en - st) / len(hs)
                for k, ch in enumerate(hs):
                    chars.append((ch, st + k * span, st + (k + 1) * span))
    want = "".join(l[0] for l in LINES)
    got = "".join(c[0] for c in chars)
    assert want == got, f"文案与配音不匹配：\n want={want}\n got ={got}"
    out, cur = [], 0
    for i, (cn, key, color, kind, layout, label) in enumerate(LINES):
        seg_ = chars[cur:cur + len(cn)]
        out.append(dict(idx=i, cn=cn, key=key, color=color, motif=kind, layout=layout,
                        label=label, start=round(seg_[0][1], 3), end=round(seg_[-1][2], 3)))
        cur += len(cn)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
