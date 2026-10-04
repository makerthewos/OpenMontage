#!/usr/bin/env python3
"""「自律」3 分钟版 · 分屏定义与渲染（黑底手绘风格）。

每屏 = (节拍 id, 字幕, 关键词, 关键词色, 母题, 版式)
屏内时长按关键词字数比例分配（见 make_zi_lv_3min.build_screen_timeline）。

成本：本模块零 API 调用（配音在 make_zi_lv_3min 的 audio 阶段）。
"""
from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

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

SUB_Y, SUB_SIZE = 1740, 50
BAR_X, BAR_Y, BAR_W, BAR_H = 60, 1852, 960, 10

# ── 分屏表 ────────────────────────────────────────────────────────
# (节拍 id, 字幕, 关键词, 关键词色, 母题, 版式)  版式: key_top | art_top
LINES = [
    # 1 hook
    ("hook", "你以为自律的人", "自律", WHITE, "calendar", "key_top"),
    ("hook", "都是靠意志力硬撑出来的", "靠意志力？", BLUE, "battery", "art_top"),
    ("hook", "但真相刚好相反，他们靠的是设计", "靠设计", GOLD, "idea", "key_top"),
    # 2 context
    ("context", "你也试过", "你也试过", WHITE, "checklist", "key_top"),
    ("context", "定闹钟早起，办健身卡", "早起", WHITE, "alarm", "art_top"),
    ("context", "列一长串计划，发誓这次一定不一样", "列计划", WHITE, "list", "art_top"),
    # 3 contrast
    ("contrast", "结果撑不过两周", "两周", BLUE, "calendar_broken", "key_top"),
    ("contrast", "然后你开始怀疑", "怀疑自己", WHITE, "question", "art_top"),
    ("contrast", "是不是自己天生就缺少毅力", "天生没毅力？", WHITE, "question", "key_top"),
    # 4 thesis
    ("thesis", "不是的。真正管用的自律", "是设计", GOLD, "blueprint", "key_top"),
    ("thesis", "是设计出来的，不是忍出来的", "不是忍", BLUE, "cross", "art_top"),
    # 5 concept
    ("concept", "心理学里有个概念叫自我损耗", "自我损耗", BLUE, "battery_half", "key_top"),
    ("concept", "意志力像肌肉，用一次就少一点", "像肌肉", WHITE, "gauge", "art_top"),
    # 6 evidence
    ("evidence", "你在公司忍了一整天", "忍一天", WHITE, "desk", "key_top"),
    ("evidence", "回家就忍不住刷手机", "刷手机", BLUE, "phone", "art_top"),
    ("evidence", "不是你没出息，是额度用完了", "额度用完", GOLD, "battery_empty", "key_top"),
    # 7 deepen
    ("deepen", "更麻烦的是，自责也在消耗额度", "自责也耗", BLUE, "battery_half", "key_top"),
    ("deepen", "你越骂自己没用，就越动不起来", "越骂越停", WHITE, "cross", "art_top"),
    # 8 research
    ("research", "研究也发现，靠意志力硬扛的人", "硬扛", WHITE, "gauge", "key_top"),
    ("research", "在压力大的时候更容易放弃", "压力大就崩", BLUE, "broken_line", "art_top"),
    # 9 turn
    ("turn", "所以真正的高手", "高手", GOLD, "crown", "key_top"),
    ("turn", "不是更能忍，而是让自己更少需要忍", "更少需要忍", WHITE, "arrow_down", "art_top"),
    # 10 principle
    ("principle", "因为环境不需要你做决定", "环境", BLUE, "room", "key_top"),
    ("principle", "它直接替你做了决定", "替你决定", WHITE, "arrow_down", "art_top"),
    # 11 method1
    ("method1", "第一，把门槛降到不可能失败", "门槛", GOLD, "stairs_dn", "key_top"),
    ("method1", "想跑步，先穿上鞋", "先穿上鞋", WHITE, "shoe", "art_top"),
    ("method1", "想读书，先翻开一页", "翻开一页", WHITE, "book", "art_top"),
    # 12 setup
    ("setup", "别一上来就挑战极限", "别太猛", BLUE, "cross", "key_top"),
    ("setup", "所有撑不下去的计划，都是因为起步太猛", "起步太猛", WHITE, "broken_line", "art_top"),
    # 13 method2
    ("method2", "第二，设计环境", "设计环境", GOLD, "room", "key_top"),
    ("method2", "让好行为变简单，让坏行为变麻烦", "简单 vs 麻烦", WHITE, "arrow_up", "art_top"),
    ("method2", "把手机放到另一个房间", "手机放远", BLUE, "phone", "key_top"),
    # 14 method3
    ("method3", "第三，换一种说法", "换说法", GOLD, "bubble", "key_top"),
    ("method3", "别说我在减肥，要说我是个会运动的人", "我是会运动的人", WHITE, "identity", "art_top"),
    # 15 method4
    ("method4", "第四，记录", "记录", GOLD, "notebook", "key_top"),
    ("method4", "不是为了打卡给别人看", "不是打卡", BLUE, "cross", "art_top"),
    ("method4", "是为了让自己看见，你真的在动", "看见在动", WHITE, "chart_up", "key_top"),
    # 16 method5
    ("method5", "第五，允许中断", "允许中断", GOLD, "broken_line", "key_top"),
    ("method5", "但不允许连续中断两次", "别连断两次", BLUE, "cross", "art_top"),
    ("method5", "断了就接上，别从头再来", "接上就行", WHITE, "arrow_up", "key_top"),
    # 17 method6
    ("method6", "第六，把新习惯挂在旧习惯后面", "挂旧习惯", GOLD, "chain", "key_top"),
    ("method6", "刷完牙，就做十个深蹲", "刷完牙→深蹲", WHITE, "stick", "art_top"),
    # 18 review
    ("review", "第七，每周花五分钟看一眼", "每周复盘", GOLD, "calendar", "key_top"),
    ("review", "什么有用，什么没用", "分辨有用", WHITE, "checklist", "art_top"),
    ("review", "然后只留有用的", "只留有用的", BLUE, "checklist", "key_top"),
    # 19 habit
    ("habit", "而习惯一旦形成", "习惯变轻", BLUE, "gauge", "key_top"),
    ("habit", "做这件事需要的力气会越来越小", "力气变小", WHITE, "arrow_down", "art_top"),
    ("habit", "就像刷牙，你从来不需要说服自己", "像刷牙", WHITE, "stick", "key_top"),
    # 20 example
    ("example", "有个作家每天只写五百字", "每天 500 字", GOLD, "notebook", "key_top"),
    ("example", "坚持十年，写出了十几本书", "十年十几本", WHITE, "book", "art_top"),
    # 21 identity
    ("identity", "你做的每一件小事", "每件小事", BLUE, "checkbox", "key_top"),
    ("identity", "都是在给一个身份投票", "身份投票", GOLD, "identity", "art_top"),
    ("identity", "投得多了，你就成了那个人", "成为那个人", WHITE, "stick", "key_top"),
    # 22 compound
    ("compound", "每天进步百分之一", "1%", GOLD, "percent", "key_top"),
    ("compound", "一年后是三十七倍", "37 倍", BLUE, "chart_up", "art_top"),
    ("compound", "每天退步百分之一，一年后几乎归零", "归零", WHITE, "chart_down", "key_top"),
    # 23 counter
    ("counter", "反过来，靠打鸡血的人", "打鸡血", BLUE, "broken_line", "key_top"),
    ("counter", "激情一退，就回到原点", "回到原点", WHITE, "chart_down", "art_top"),
    # 24 mental
    ("mental", "你不需要每天都赢", "不必每天赢", GOLD, "crown", "key_top"),
    ("mental", "你只需要别在输的那一天，把牌桌掀了", "别掀牌桌", WHITE, "cross", "art_top"),
    # 25 turn2
    ("turn2", "最狠的自律", "最狠的自律", GOLD, "crown", "key_top"),
    ("turn2", "是让自律这件事，变得不必要", "变得不必要", WHITE, "cross", "art_top"),
    # 26 landing
    ("landing", "今晚挑一件小事", "一件小事", WHITE, "checkbox", "key_top"),
    ("landing", "把第一步拆到三分钟能做完", "3 分钟", GOLD, "timer", "art_top"),
    ("landing", "做完就去睡", "做完就睡", BLUE, "moon", "key_top"),
    # 27 cta
    ("cta", "别等有动力才开始", "别等动力", BLUE, "cross", "key_top"),
    ("cta", "三分钟到了，你就已经赢了今天", "赢了今天", GOLD, "checklist", "art_top"),
    ("cta", "先动起来，动力会自己跟上", "先动起来", WHITE, "stick_walk", "key_top"),
]


# ── 手绘线条 ──────────────────────────────────────────────────────
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


def seg(d, p0, p1, seed=0, width=6, fill=WHITE, amp=2.2):
    n = max(6, int(math.dist(p0, p1) / 14))
    poly(d, wobble(p0, p1, n, amp, seed), width, fill)


def rect(d, box, seed=0, width=6, fill=WHITE, r=12):
    x0, y0, x1, y1 = box
    seg(d, (x0 + r, y0), (x1 - r, y0), seed, width, fill)
    seg(d, (x1, y0 + r), (x1, y1 - r), seed + 1, width, fill)
    seg(d, (x1 - r, y1), (x0 + r, y1), seed + 2, width, fill)
    seg(d, (x0, y0 + r), (x0, y1 - r), seed + 3, width, fill)


def circle(d, cx, cy, r, seed=0, width=6, fill=WHITE):
    rng = random.Random(seed)
    pts = [(cx + (r + rng.uniform(-2.5, 2.5)) * math.cos(2 * math.pi * i / 28),
            cy + (r + rng.uniform(-2.5, 2.5)) * math.sin(2 * math.pi * i / 28)) for i in range(29)]
    d.line(pts, fill=fill, width=width, joint="curve")


def ellipse(d, cx, cy, rx, ry, seed=0, width=5, fill=None):
    """带抖动的手绘椭圆（贴合文字的圈画用）。"""
    rng = random.Random(seed)
    pts = [(cx + (rx + rng.uniform(-2.5, 2.5)) * math.cos(2 * math.pi * i / 40),
            cy + (ry + rng.uniform(-2.5, 2.5)) * math.sin(2 * math.pi * i / 40)) for i in range(41)]
    d.line(pts, fill=fill, width=width, joint="curve")


def stick(d, x, y, h=150, pose="stand", seed=0, fill=WHITE, width=6):
    hr = h * 0.13
    circle(d, x, y - h + hr, hr, seed, width, fill)
    hip = (x, y - h * 0.45)
    seg(d, (x, y - h + 2 * hr), hip, seed + 1, width, fill)
    poses = {
        "stand": [((x, hip[1]), (x - h * .22, y)), ((x, hip[1]), (x + h * .22, y)),
                  ((x, y - h * .78), (x - h * .30, y - h * .55)), ((x, y - h * .78), (x + h * .30, y - h * .55))],
        "walk": [((x, hip[1]), (x - h * .34, y)), ((x, hip[1]), (x + h * .30, y - h * .12)),
                 ((x, y - h * .78), (x - h * .34, y - h * .60)), ((x, y - h * .78), (x + h * .34, y - h * .62))],
        "sit": [((x, hip[1]), (x + h * .34, hip[1])), ((x + h * .34, hip[1]), (x + h * .34, y)),
                ((x, y - h * .78), (x + h * .28, y - h * .62))],
    }[pose if pose in ("stand", "walk", "sit") else "stand"]
    for i, (a, b) in enumerate(poses):
        seg(d, a, b, seed + 2 + i, width, fill)


# ── 母题库 ────────────────────────────────────────────────────────
def motif(d, kind, cx, cy, seed=0):
    k = kind
    if k == "calendar":
        for r in range(2):
            for c in range(4):
                box = (cx - 208 + c * 112, cy - 84 + r * 112, cx - 124 + c * 112, cy + 6 + r * 112)
                rect(d, box, seed + r * 4 + c, 5)
                if r * 4 + c < 5:
                    seg(d, (box[0] + 14, box[1] + 50), (box[0] + 34, box[1] + 74), seed + 20 + c, 6)
                    seg(d, (box[0] + 34, box[1] + 74), (box[0] + 70, box[1] + 20), seed + 21 + c, 6)
    elif k == "calendar_broken":
        for c in range(6):
            box = (cx - 240 + c * 82, cy - 60, cx - 178 + c * 82, cy + 40)
            rect(d, box, seed + c, 5, DIM if c > 1 else WHITE)
        poly(d, wobble((cx - 250, cy - 100), (cx + 250, cy + 80), 26, 3.0, seed + 9), 7, GOLD)
    elif k in ("battery", "battery_half", "battery_empty"):
        rect(d, (cx - 170, cy - 80, cx + 130, cy + 80), seed)
        seg(d, (cx + 130, cy - 30), (cx + 165, cy - 30), seed, 9)
        seg(d, (cx + 165, cy - 30), (cx + 165, cy + 30), seed, 9)
        seg(d, (cx + 130, cy + 30), (cx + 165, cy + 30), seed, 9)
        fill = {"battery": 3, "battery_half": 2, "battery_empty": 0}[k]
        for i in range(3):
            x = cx - 140 + i * 88
            rect(d, (x, cy - 52, x + 66, cy + 52), seed + 10 + i, 5 if i < fill else 3,
                 WHITE if i < fill else DIM, r=6)
    elif k == "idea":
        circle(d, cx, cy - 20, 66, seed, 6)
        seg(d, (cx, cy - 20), (cx, cy + 26), seed + 1, 6)
        seg(d, (cx - 26, cy + 46), (cx + 26, cy + 46), seed + 2, 6)
        seg(d, (cx - 20, cy + 66), (cx + 20, cy + 66), seed + 3, 6)
        for i in range(6):
            a = 2 * math.pi * i / 6
            seg(d, (cx + 96 * math.cos(a), cy - 20 + 96 * math.sin(a)),
                (cx + 130 * math.cos(a), cy - 20 + 130 * math.sin(a)), seed + 10 + i, 5, GOLD)
    elif k == "checklist":
        for i in range(3):
            y = cy - 76 + i * 76
            rect(d, (cx - 190, y - 24, cx - 146, y + 20), seed + i, 5, r=6)
            seg(d, (cx - 110, y), (cx + 90 - i * 30, y), seed + 10 + i, 5, WHITE if i == 0 else DIM)
        seg(d, (cx - 184, cy - 4), (cx - 168, cy + 14), seed + 30, 6, GOLD)
        seg(d, (cx - 168, cy + 14), (cx - 140, cy - 20), seed + 31, 6, GOLD)
    elif k == "alarm":
        circle(d, cx, cy, 104, seed, 7)
        for i in range(12):
            a = 2 * math.pi * i / 12
            seg(d, (cx + 84 * math.cos(a), cy + 84 * math.sin(a)),
                (cx + 98 * math.cos(a), cy + 98 * math.sin(a)), seed + i, 5, DIM if i % 3 else WHITE)
        seg(d, (cx, cy), (cx, cy - 58), seed + 30, 7)
        seg(d, (cx, cy), (cx + 44, cy + 24), seed + 31, 7, GOLD)
        seg(d, (cx - 96, cy - 96), (cx - 60, cy - 130), seed + 40, 8)
        seg(d, (cx + 96, cy - 96), (cx + 60, cy - 130), seed + 41, 8)
    elif k == "list":
        for i in range(5):
            y = cy - 110 + i * 52
            seg(d, (cx - 200, y), (cx + 200 - i * 24, y), seed + i, 5, WHITE if i % 2 == 0 else DIM)
    elif k == "question":
        poly(d, wobble((cx - 60, cy - 70), (cx + 20, cy - 90), 12, 2.5, seed), 8)
        poly(d, wobble((cx + 20, cy - 90), (cx + 50, cy - 20), 10, 2.5, seed), 8)
        poly(d, wobble((cx + 50, cy - 20), (cx, cy + 30), 10, 2.5, seed), 8)
        seg(d, (cx, cy + 76), (cx, cy + 100), seed + 9, 9)
    elif k == "blueprint":
        rect(d, (cx - 210, cy - 130, cx + 210, cy + 130), seed, 5)
        for i in range(3):
            seg(d, (cx - 150, cy - 60 + i * 50), (cx + 150 - i * 40, cy - 60 + i * 50), seed + i, 4, DIM)
        seg(d, (cx - 150, cy - 90), (cx + 60, cy - 90), seed + 9, 6, GOLD)
    elif k == "cross":
        circle(d, cx, cy, 120, seed, 7, DIM)
        poly(d, wobble((cx - 62, cy - 62), (cx + 62, cy + 62), 14, 3.0, seed + 1), 10, GOLD)
        poly(d, wobble((cx + 62, cy - 62), (cx - 62, cy + 62), 14, 3.0, seed + 2), 10, GOLD)
    elif k == "gauge":
        for i in range(9):
            a = math.pi + math.pi * i / 8
            seg(d, (cx + 130 * math.cos(a), cy + 130 * math.sin(a)),
                (cx + 165 * math.cos(a), cy + 165 * math.sin(a)), seed + i, 6, WHITE if i < 5 else DIM)
        seg(d, (cx, cy), (cx + 90 * math.cos(math.pi * 1.35), cy + 90 * math.sin(math.pi * 1.35)), seed + 20, 7, GOLD)
        circle(d, cx, cy, 12, seed + 21, 7)
    elif k == "desk":
        seg(d, (cx - 230, cy + 70), (cx + 230, cy + 70), seed, 7)
        rect(d, (cx - 150, cy - 90, cx + 60, cy + 40), seed + 1, 5)
        seg(d, (cx + 120, cy + 70), (cx + 120, cy - 40), seed + 2, 6)
        circle(d, cx + 120, cy - 70, 30, seed + 3, 6)
    elif k == "phone":
        rect(d, (cx - 90, cy - 150, cx + 90, cy + 150), seed, 7, r=20)
        seg(d, (cx - 40, cy - 118), (cx + 40, cy - 118), seed + 1, 5, DIM)
        for i in range(3):
            seg(d, (cx - 56, cy - 40 + i * 40), (cx + 56, cy - 40 + i * 40), seed + 2 + i, 4, DIM)
    elif k == "broken_line":
        poly(d, wobble((cx - 240, cy - 40), (cx - 60, cy - 70), 14, 3, seed), 7)
        poly(d, wobble((cx - 60, cy - 70), (cx - 20, cy + 40), 8, 3, seed + 1), 7)
        poly(d, wobble((cx + 20, cy - 20), (cx + 240, cy + 60), 16, 3, seed + 2), 7, DIM)
    elif k == "crown":
        poly(d, wobble((cx - 150, cy + 40), (cx + 150, cy + 40), 20, 3, seed), 7)
        poly(d, wobble((cx - 150, cy + 40), (cx - 110, cy - 70), 10, 2.5, seed + 1), 6)
        poly(d, wobble((cx - 110, cy - 70), (cx - 40, cy - 10), 10, 2.5, seed + 2), 6)
        poly(d, wobble((cx - 40, cy - 10), (cx, cy - 90), 10, 2.5, seed + 3), 6)
        poly(d, wobble((cx, cy - 90), (cx + 40, cy - 10), 10, 2.5, seed + 4), 6)
        poly(d, wobble((cx + 40, cy - 10), (cx + 110, cy - 70), 10, 2.5, seed + 5), 6)
        poly(d, wobble((cx + 110, cy - 70), (cx + 150, cy + 40), 10, 2.5, seed + 6), 6)
    elif k in ("arrow_up", "arrow_down"):
        s = -1 if k == "arrow_up" else 1
        seg(d, (cx, cy - 70 * s), (cx, cy + 80 * s), seed, 8)
        seg(d, (cx - 46, cy + 26 * s), (cx, cy + 86 * s), seed + 1, 8)
        seg(d, (cx + 46, cy + 26 * s), (cx, cy + 86 * s), seed + 2, 8)
    elif k == "room":
        rect(d, (cx - 200, cy - 140, cx + 200, cy + 140), seed, 6)
        rect(d, (cx - 150, cy + 20, cx - 40, cy + 140), seed + 1, 5)
        rect(d, (cx + 60, cy - 60, cx + 160, cy + 40), seed + 2, 5, DIM)
    elif k == "stairs_dn":
        x, y = cx - 230, cy - 110
        for i in range(4):
            seg(d, (x, y), (x + 96, y), seed + i, 6)
            seg(d, (x + 96, y), (x + 96, y + 56), seed + i, 6)
            x, y = x + 96, y + 56
        seg(d, (x, y), (x + 96, y), seed + 9, 6)
        stick(d, cx + 40, cy + 116, 130, "walk", seed + 60)
    elif k == "shoe":
        seg(d, (cx - 190, cy + 60), (cx - 190, cy - 6), seed, 6)
        seg(d, (cx - 190, cy - 6), (cx - 60, cy - 40), seed, 6)
        seg(d, (cx - 60, cy - 40), (cx + 80, cy + 6), seed, 6)
        seg(d, (cx + 80, cy + 6), (cx + 190, cy + 10), seed, 6)
        seg(d, (cx - 190, cy + 60), (cx + 190, cy + 64), seed + 1, 7)
        for i in range(3):
            seg(d, (cx - 90, cy - 32 + i * 16), (cx - 30, cy - 14 + i * 16), seed + 10 + i, 4)
    elif k == "book":
        seg(d, (cx, cy - 70), (cx, cy + 76), seed, 6)
        seg(d, (cx, cy - 70), (cx - 180, cy - 36), seed + 1, 6)
        seg(d, (cx - 180, cy - 36), (cx - 170, cy + 88), seed + 2, 6)
        seg(d, (cx - 170, cy + 88), (cx, cy + 76), seed + 3, 6)
        seg(d, (cx, cy - 70), (cx + 180, cy - 36), seed + 4, 6)
        seg(d, (cx + 180, cy - 36), (cx + 170, cy + 88), seed + 5, 6)
        seg(d, (cx + 170, cy + 88), (cx, cy + 76), seed + 6, 6)
        for i in range(3):
            seg(d, (cx - 150, cy - 10 + i * 26), (cx - 30, cy - 4 + i * 26), seed + 10 + i, 4, DIM)
    elif k == "notebook":
        rect(d, (cx - 160, cy - 150, cx + 150, cy + 150), seed, 6)
        for i in range(5):
            seg(d, (cx - 120, cy - 100 + i * 46), (cx + 110 - i * 12, cy - 100 + i * 46), seed + i, 4, WHITE if i < 2 else DIM)
        seg(d, (cx - 160, cy - 150), (cx - 160, cy + 150), seed + 9, 8, GOLD)
    elif k == "chart_up":
        seg(d, (cx - 220, cy + 100), (cx + 220, cy + 100), seed, 5, DIM)
        seg(d, (cx - 220, cy + 100), (cx - 220, cy - 130), seed, 5, DIM)
        poly(d, wobble((cx - 200, cy + 70), (cx + 180, cy - 110), 22, 3, seed + 1), 7, GOLD)
        seg(d, (cx + 180, cy - 110), (cx + 130, cy - 116), seed + 2, 7, GOLD)
    elif k == "chart_down":
        seg(d, (cx - 220, cy + 100), (cx + 220, cy + 100), seed, 5, DIM)
        poly(d, wobble((cx - 200, cy - 90), (cx + 190, cy + 70), 22, 3, seed + 1), 7, DIM)
        poly(d, wobble((cx - 40, cy + 70), (cx + 200, cy + 74), 10, 2, seed + 2), 5, DIM)
    elif k == "percent":
        circle(d, cx - 80, cy - 60, 46, seed, 6)
        circle(d, cx + 90, cy + 70, 46, seed + 1, 6)
        poly(d, wobble((cx + 130, cy - 120), (cx - 130, cy + 120), 24, 3, seed + 2), 7, GOLD)
    elif k == "bubble":
        rect(d, (cx - 220, cy - 110, cx + 150, cy + 60), seed, 6, r=30)
        poly(d, wobble((cx - 40, cy + 58), (cx - 70, cy + 140), 8, 2, seed + 1), 6)
        poly(d, wobble((cx - 70, cy + 140), (cx + 30, cy + 56), 8, 2, seed + 2), 6)
        for i in range(3):
            seg(d, (cx - 170, cy - 50 + i * 40), (cx + 60 - i * 30, cy - 50 + i * 40), seed + 3 + i, 4, DIM)
    elif k == "identity":
        circle(d, cx, cy - 60, 56, seed, 6)
        seg(d, (cx, cy - 4), (cx, cy + 90), seed + 1, 7)
        seg(d, (cx, cy + 20), (cx - 70, cy + 60), seed + 2, 6)
        seg(d, (cx, cy + 20), (cx + 70, cy + 60), seed + 3, 6)
        seg(d, (cx - 110, cy + 150), (cx + 110, cy + 150), seed + 4, 6, GOLD)
    elif k == "timer":
        circle(d, cx, cy, 118, seed, 7)
        for i in range(12):
            a = 2 * math.pi * i / 12
            px, py = cx + 100 * math.cos(a), cy + 100 * math.sin(a)
            seg(d, (px, py), (px + 14 * math.cos(a), py + 14 * math.sin(a)), seed + i, 5, DIM if i % 3 else WHITE)
        seg(d, (cx, cy), (cx, cy - 74), seed + 30, 7)
        seg(d, (cx, cy), (cx + 54, cy + 30), seed + 31, 7, GOLD)
        seg(d, (cx - 40, cy - 140), (cx + 40, cy - 140), seed + 32, 8)
    elif k == "moon":
        circle(d, cx, cy, 110, seed, 7)
        d.ellipse((cx - 40, cy - 140, cx + 200, cy + 100), fill=BG)
        for i in range(3):
            seg(d, (cx - 200 + i * 40, cy - 160), (cx - 170 + i * 40, cy - 190), seed + i, 5, GOLD)
    elif k == "chain":
        for i in range(2):
            circle(d, cx - 70 + i * 140, cy, 62, seed + i, 6)
        seg(d, (cx - 20, cy), (cx + 20, cy), seed + 9, 7, GOLD)
    elif k == "stick":
        stick(d, cx, cy + 120, 210, "stand", seed)
    elif k == "stick_walk":
        stick(d, cx, cy + 120, 210, "walk", seed)
        for i in range(3):
            seg(d, (cx + 120 + i * 26, cy + 40), (cx + 160 + i * 26, cy + 40), seed + i, 5, DIM)
    else:                                            # 兜底：一横线
        seg(d, (cx - 150, cy), (cx + 150, cy), seed, 7)



# ── 批注：给关键屏加一句手写小注 + 指示线 ──────────────────────────
# 按**关键词**匹配（不按下标——分屏一改下标就会串屏）
ANNOTATIONS = {
    "靠意志力？": "不是懒，是额度",
    "自我损耗": "意志力是有限资源",
    "忍一天": "忍一天 = 花一天",
    "越骂越停": "自责也在扣额度",
    "门槛": "低到不可能失败",
    "先穿上鞋": "先做，别想",
    "设计环境": "环境替你决定",
    "手机放远": "少一次挣扎",
    "我是会运动的人": "身份先于行为",
    "看见在动": "记录 = 看见进步",
    "允许中断": "断一次不算失败",
    "挂旧习惯": "挂在已有习惯后",
    "每周复盘": "每周只留有用的",
    "习惯变轻": "像刷牙一样",
    "每天 500 字": "十年十几本",
    "身份投票": "每件小事 = 一票",
    "1%": "1% × 365 ≈ 37 倍",
    "打鸡血": "激情会退，系统不会",
    "3 分钟": "三分钟就够",
    "先动起来": "别等动力",
}

STEP_BEATS = ["method1", "setup", "method2", "method3", "method4", "method5", "method6", "review"]


def doodle_sparkle(d, x, y, seed=0, color=GOLD, s=1.0):
    """手绘小星：三笔交叉。"""
    for i, (dx, dy) in enumerate(((1, 0), (0.5, 0.5), (0, 1), (-0.5, 0.5))):
        seg(d, (x - 14 * s * dx, y - 14 * s * dy), (x + 14 * s * dx, y + 14 * s * dy), seed + i, 4, color)


def draw_annotation(d, note, direction, cx, cy, seed=0):
    """在手绘批注：一行小字 + 一条指向线。"""
    f = ImageFont.truetype(FONT_HAND, 46)
    w = f.getlength(note)
    x = cx - w / 2 if direction == "left" else cx - w / 2
    y = cy
    # 指向线：从批注末端甩出一条弯钩
    ax = (x + w + 18) if direction == "right" else (x - 18)
    poly(d, wobble((ax, y + 10), (ax + (70 if direction == "right" else -70), y - 26), 10, 3, seed), 4, DIM)
    d.text((cx, y), note, font=f, fill=DIM, anchor="mm")


def draw_step_badge(d, step, total, cx, cy, color=GOLD):
    """方法屏的步骤徽章 + 进度点。"""
    f = ImageFont.truetype(FONT_PING, 40, index=IDX_SC_SEMIBOLD)
    d.text((cx, cy), f"第 {step} 步 / {total}", font=f, fill=color, anchor="mm")
    for i in range(total):
        x = cx - (total - 1) * 17 + i * 34
        filled = i < step
        d.ellipse((x - 7, cy + 42, x + 7, cy + 56), outline=color if filled else TRACK,
                  width=3, fill=color if filled else None)


def fit_font(path, size, text, max_w, index=0):
    f = ImageFont.truetype(path, size, index=index)
    while f.getlength(text) > max_w and size > 40:
        size -= 8
        f = ImageFont.truetype(path, size, index=index)
    return f


def render_base(idx: int, scr: dict, total: int, progress: float = 1.0) -> Image.Image:
    """progress: 入画动画进度 0→1（关键词与线稿淡入 + 轻微放大）。"""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_lab = ImageFont.truetype(FONT_PING, 36, index=IDX_SC_SEMIBOLD)
    d.text((66, 90), scr.get("label", ""), font=f_lab, fill=DIM)
    d.text((W - 66, 90), f"{idx+1:02d}/{total}", font=f_lab, fill=DIM, anchor="ra")

    key, color, kind = scr["key"], scr["color"], scr["motif"]
    key_y, art_y = (int(H * 0.40), int(H * 0.645)) if scr["layout"] == "key_top" else (int(H * 0.685), int(H * 0.365))

    # 关键词：淡入 + 从 0.94 放大到 1.0
    kp = min(1.0, progress / 0.6)
    f_key = fit_font(FONT_HAND, 190, key, W - 240)
    if kp > 0:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((W // 2, key_y), key, font=f_key, fill=color + (int(255 * kp),), anchor="mm")
        if kp < 1:
            s = 0.94 + 0.06 * kp
            layer = layer.resize((int(W * s), int(H * s)), Image.LANCZOS)
            img.paste(layer, ((W - layer.width) // 2, (H - layer.height) // 2), layer)
        else:
            img.paste(layer, (0, 0), layer)
    if kp >= 1:                                   # 装饰线/圈在关键词之后出现
        kw = f_key.getlength(key)
        if idx % 3 == 1 and kw <= 620:            # 圈画：椭圆贴合文字，别吞掉线稿
            ellipse(d, W // 2, key_y, kw / 2 + 36, 104, idx + 5, 5, color)
        else:                                     # 字太长就退回下划线
            seg(d, (W // 2 - min(kw / 2 + 20, 380), key_y + 118),
                (W // 2 + min(kw / 2 + 20, 380), key_y + 118), idx, 6, color, 3.2)

    # 线稿母题：稍晚入场，同样淡入 + 放大
    mp = min(1.0, max(0.0, (progress - 0.25) / 0.55))
    if mp > 0:
        layer = Image.new("RGBA", (900, 620), (0, 0, 0, 0))
        motif(ImageDraw.Draw(layer), kind, 450, 310, seed=idx * 17 + 3)
        layer = layer.resize((int(900 * 1.12), int(620 * 1.12)), Image.LANCZOS)
        if mp < 1:
            a = layer.split()[3].point(lambda v: int(v * mp))
            layer.putalpha(a)
            s = 0.9 + 0.1 * mp
            layer = layer.resize((int(layer.width * s), int(layer.height * s)), Image.LANCZOS)
        img.paste(layer, (W // 2 - layer.width // 2, art_y - layer.height // 2), layer)

    # 批注 / 步骤徽章 / 星点：最后出现
    late = max(0.0, (progress - 0.6) / 0.4)
    if late > 0:
        note = ANNOTATIONS.get(key)
        if note:
            tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw_annotation(ImageDraw.Draw(tmp), note, "left", W // 2, int(H * 0.80), seed=idx)
            tmp.putalpha(tmp.split()[3].point(lambda v: int(v * late)))
            img.paste(tmp, (0, 0), tmp)
        if scr["beat"] in STEP_BEATS:
            step = STEP_BEATS.index(scr["beat"]) + 1
            badge = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw_step_badge(ImageDraw.Draw(badge), step, len(STEP_BEATS), W // 2, int(H * 0.175))
            badge.putalpha(badge.split()[3].point(lambda v: int(v * late)))
            img.paste(badge, (0, 0), badge)
        if idx % 4 == 2:
            sp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            doodle_sparkle(ImageDraw.Draw(sp), 190, 470, seed=idx)
            doodle_sparkle(ImageDraw.Draw(sp), W - 200, 1420, seed=idx + 3, s=0.8)
            sp.putalpha(sp.split()[3].point(lambda v: int(v * late)))
            img.paste(sp, (0, 0), sp)

    # 底部渐隐 + 字幕 + 进度条轨道（进度条填充由 overlay 负责）
    grad = Image.new("L", (1, 260))
    for i in range(260):
        grad.putpixel((0, i), int(150 * (i / 260) ** 1.6))
    img.paste(Image.new("RGB", (W, 260), (0, 0, 0)), (0, H - 260), grad.resize((W, 260)))
    d = ImageDraw.Draw(img)
    f_sub = ImageFont.truetype(FONT_PING, SUB_SIZE, index=IDX_SC_SEMIBOLD)
    d.text((W // 2, SUB_Y), scr["cn"], font=f_sub, fill=GOLD, anchor="mm")
    d.rounded_rectangle((BAR_X, BAR_Y, BAR_X + BAR_W, BAR_Y + BAR_H), BAR_H // 2, fill=TRACK)
    return img


ANIM_FRAMES = 14          # 每屏入画动画帧数（约 0.47s）


def render_frames(screens: list[dict], total: float, project: Path) -> Path:
    """每屏生成 动画段(ANIM_FRAMES 帧) + 静止段，再编码拼接。

    底图静止，只有入画动画需要逐帧；进度条另出轻量序列（见 render_bar_strips）。
    """
    work = project / "work"
    shots = work / "screens"
    anim = work / "anim"
    segs = work / "segs"
    for dpath in (shots, anim, segs):
        dpath.mkdir(parents=True, exist_ok=True)
        for f in dpath.glob("*.png" if dpath is not anim else "*.png"):
            f.unlink()
        for f in dpath.glob("*.mp4"):
            f.unlink()

    seg_files = []
    for i, s in enumerate(screens):
        dur = max(0.2, s["end"] - s["start"])
        a_dur = min(ANIM_FRAMES / FPS, dur * 0.5)
        n_anim = max(2, int(a_dur * FPS))

        final = render_base(i, s, len(screens), progress=1.0)
        final.save(shots / f"{i:03d}.png")

        adir = anim / f"{i:03d}"
        adir.mkdir(exist_ok=True)
        for k in range(n_anim):
            render_base(i, s, len(screens), progress=(k + 1) / n_anim).save(adir / f"{k:03d}.png")

        seg_a = segs / f"{i:03d}_a.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS),
                        "-i", str(adir / "%03d.png"), "-t", f"{n_anim / FPS:.3f}",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                        "-pix_fmt", "yuv420p", str(seg_a)], check=True)
        hold = max(0.04, dur - n_anim / FPS)
        seg_b = segs / f"{i:03d}_b.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1",
                        "-i", str(shots / f"{i:03d}.png"), "-t", f"{hold:.3f}",
                        "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "16", "-pix_fmt", "yuv420p", str(seg_b)], check=True)
        seg_files += [seg_a, seg_b]

    lst = work / "concat.txt"
    lst.write_text("\n".join(f"file '{p}'" for p in seg_files) + "\n", encoding="utf-8")
    silent = work / "silent.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(lst), "-c", "copy", "-t", f"{total:.3f}", str(silent)], check=True)
    print(f"底图 {len(screens)} 张 + 入画动画 {len(screens)*ANIM_FRAMES} 帧 → 静默视频 {total:.1f}s")
    return silent


def render_bar_strips(total: float, project: Path) -> Path:
    """进度条只画 1080×20 的小图，overlay 上去即可——避免重渲整帧。"""
    bars = project / "work" / "bars"
    bars.mkdir(parents=True, exist_ok=True)
    for f in bars.glob("*.png"):
        f.unlink()
    n = int(total * FPS)
    for i in range(n):
        img = Image.new("RGBA", (W, 28), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        w = int(BAR_W * min(1.0, (i / FPS) / total))
        y0 = BAR_Y - (BAR_Y - 6) + 6      # 条带内的纵向偏移：让填充对齐底图轨道
        if w > 0:
            d.rounded_rectangle((BAR_X, 12, BAR_X + w, 12 + BAR_H), BAR_H // 2, fill=GOLD + (255,))
        img.save(bars / f"{i:05d}.png")
    print(f"进度条序列 {n} 张")
    return bars


def assemble(screens: list[dict], total: float, project: Path, timing: dict) -> None:
    render = project / "render"
    render.mkdir(parents=True, exist_ok=True)
    out = render / "final.mp4"
    silent = project / "work" / "silent.mp4"
    bars = project / "work" / "bars"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-i", str(silent),
        "-framerate", str(FPS), "-i", str(bars / "%05d.png"),
        "-i", str(project / "audio" / "narration.wav"),
        "-filter_complex",
        f"[0:v][1:v]overlay=0:{BAR_Y - 12}:format=auto[v1];"
        f"[v1]fade=t=in:st=0:d=0.4,fade=t=out:st={total-0.8:.3f}:d=0.8,format=yuv420p[v];"
        # 人声后处理链（原始 TTS 是"消音室干声"，直接听偏电子味）：
        # ① 削 200Hz 浑浊 ② 提 3k/5k 存在感 ③ 降调 4% 加厚
        # ④ 轻压缩压住起伏 ⑤ 统一到 -14 LUFS
        f"[2:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
        f"equalizer=f=200:t=q:w=1.5:g=-3,equalizer=f=3000:t=q:w=1.0:g=3,"
        f"equalizer=f=5000:t=q:w=1.5:g=2,"
        f"asetrate=24000*0.96,aresample=48000,atempo=1.0417,"
        f"acompressor=threshold=-20dB:ratio=2.5:attack=10:release=100,"
        f"loudnorm=I=-14:TP=-1.5:LRA=9[a]",
        "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)
