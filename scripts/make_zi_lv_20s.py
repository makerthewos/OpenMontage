"""20 秒 · 主题「自律」——从节拍表到成片的参考实现。

与 `make_how_to_read_a_book.py` 的区别：那一条是手写 BEATS 常量，
这一条的**唯一真源是 beat-sheet.yaml**（正是 skills/06 阶段 2 的产物），
即：节拍表 → 校验 → 配音 → 实测时间轴 → edit_decisions → 渲染。

成本：全组件场景（无配图、无视频生成）+ 豆包配音（79 字，按字符计费，约几分钱）。

Run:
    python scripts/make_zi_lv_20s.py --stage audio     # 配音 + 实测时间轴
    python scripts/make_zi_lv_20s.py --stage render    # 生成 artifact 并渲染
    python scripts/make_zi_lv_20s.py                   # 全流程
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT = "zi-lv-20s"
ROOT = Path(__file__).resolve().parent.parent
PDIR = ROOT / "projects" / PROJECT
BEAT_SHEET = PDIR / "beat-sheet.yaml"
PLAYBOOK = "clean-professional"
DOUBAO_VOICE = "zh_female_vv_uranus_bigtts"
FPS = 30
TAIL_SILENCE = 0.6          # 收尾留白，避免最后一句被切断


def load_beats() -> tuple[dict, list[dict], dict]:
    """节拍表是唯一真源：meta（含 meta 外的 style）+ beats 一起读出来。"""
    import yaml
    data = yaml.safe_load(BEAT_SHEET.read_text(encoding="utf-8"))
    return data["meta"], data["beats"], (data.get("style") or {})


def ffprobe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True).stdout.strip()
    return float(out or 0)


# ── 阶段 5a：配音（逐拍合成 + 非均匀停顿）────────────────────────────


def stage_audio(meta: dict, beats: list[dict]) -> dict:
    from tools.tool_registry import registry
    registry.discover()
    doubao = registry._tools["doubao_tts"]
    if doubao.get_status().value != "available":
        raise SystemExit("doubao_tts 不可用：检查 DOUBAO_SPEECH_API_KEY")

    audio_dir = PDIR / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    pieces, silences, per_beat = [], [], []
    cursor = 0.0
    for idx, beat in enumerate(beats):
        pause = float(beat.get("pause_before") or 0.0)
        beat_start = cursor + pause
        raw = audio_dir / f"_beat_{idx + 1}.wav"
        result = doubao.execute({
            "text": beat["narration"], "voice_id": DOUBAO_VOICE,
            "format": "wav", "sample_rate": 24000,
            "enable_timestamp": True, "return_usage": True,
            "output_path": str(raw),
        })
        if not result.success:
            raise SystemExit(f"TTS 失败（{beat['id']}）：{result.error}")
        dur = float((result.data or {}).get("duration_seconds") or 0) or ffprobe_duration(raw)
        per_beat.append({"id": beat["id"], "start": round(beat_start, 3),
                         "end": round(beat_start + dur, 3)})
        pieces.append(raw)
        silences.append(pause)
        cursor = beat_start + dur
        predicted = beat["chars"] / 4.25
        print(f"  {beat['id']:10s} 实测 {dur:6.3f}s（预测 {predicted:5.2f}s，"
              f"偏差 {(dur - predicted) / predicted:+.1%}）  前停 {pause:.2f}s")

    # 停顿 + 各拍 → 单条 narration.wav
    lines = []
    for i, piece in enumerate(pieces):
        sil = audio_dir / f"_sil_{i}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                        "-i", "anullsrc=r=24000:cl=mono", "-t", f"{silences[i]:.3f}", str(sil)],
                       capture_output=True, text=True)
        lines += [f"file '{sil.resolve()}'", f"file '{piece.resolve()}'"]
    tail = audio_dir / "_sil_tail.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "anullsrc=r=24000:cl=mono", "-t", str(TAIL_SILENCE), str(tail)],
                   capture_output=True, text=True)
    lines.append(f"file '{tail.resolve()}'")

    listing = audio_dir / "_concat.txt"
    listing.write_text("\n".join(lines), encoding="utf-8")
    narration = PDIR / "assets" / "audio" / "narration.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(listing), "-ar", "24000", "-ac", "1", str(narration)],
                   capture_output=True, text=True)
    for tmp in pieces + [audio_dir / f"_sil_{i}.wav" for i in range(len(pieces))] + [tail, listing]:
        Path(tmp).unlink(missing_ok=True)

    timing = {
        "engine": f"doubao:{DOUBAO_VOICE}",
        "target_seconds": meta["target_seconds"],
        "narration_seconds": round(ffprobe_duration(narration), 3),
        "beats": per_beat,
    }
    (PDIR / "artifacts").mkdir(parents=True, exist_ok=True)
    (PDIR / "artifacts" / "narration_timing.json").write_text(
        json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  narration.wav 实测 {timing['narration_seconds']:.3f}s"
          f"（目标 {meta['target_seconds']}s，"
          f"{(timing['narration_seconds'] - meta['target_seconds']) / meta['target_seconds']:+.1%}）")
    return timing


# ── 阶段 6–7：edit_decisions → 渲染 ──────────────────────────────────

# 屏上文字（与旁白分离：旁白在音频里，这里只放画面上的字）
ON_SCREEN = {
    "hook": {"text": "自律，不靠意志力", "subtitle": "靠意志力的，撑不过一周"},
    "landing": {"text": "今晚挑一件小事\n把第一步拆到三分钟能做完"},
}
# 长拍拆刀时的两屏文字（见 stage_render 的 7 秒规则）
SPLIT_TEXT = {
    "proof": ("意志力是消耗品\n用完就没了",
              "把门槛降到不可能失败\n想跑步，先穿上鞋\n想读书，先翻开一页"),
}


def make_cut(cut_id: str, scene: str, start: float, end: float,
             text: str | None, subtitle: str | None = None, **extra) -> dict:
    cut = {
        "id": cut_id,
        "type": scene,
        "source": f"component:{scene}",          # schema 必填；组件场景用占位
        "in_seconds": round(start, 3),
        "out_seconds": round(end, 3),            # 绝对时间轴位置（见 skills/05 陷阱 1）
        "layer": "primary",
    }
    if text:
        cut["text"] = text
    if subtitle:
        cut["subtitle"] = subtitle
    if scene == "callout":
        cut["callout_type"] = extra.get("callout_type", "tip")
    if scene == "text_card":
        cut["fontSize"] = 64
    return cut


def stage_render(meta: dict, beats: list[dict], timing: dict,
                 style: dict | None = None,
                 playbook_override: str | None = None,
                 out_path: Path | None = None) -> dict:
    """阶段 6–7。风格三层：playbook → theme_overrides → per_beat（见 skills/07）。"""
    style = style or {}
    from tools.tool_registry import registry
    from tools.video.video_compose import VideoCompose
    registry.discover()

    audio = (PDIR / "assets" / "audio" / "narration.wav").resolve()
    if not audio.is_file():
        raise SystemExit("先跑 --stage audio")

    cuts = []
    wins = timing["beats"]
    for i, (beat, win) in enumerate(zip(beats, wins)):
        # 窗口连续覆盖：每刀延伸到下一拍的起点（首刀从 0 开始），
        # 这样停顿期间画面是"定格"而不是"空白"——满足 edit 阶段的
        # "全片时间轴无空洞"判据。旁白的停顿由音频负责，与画面无关。
        start = 0.0 if i == 0 else win["start"]
        end = wins[i + 1]["start"] if i + 1 < len(wins) else win["end"]
        # 超过 7 秒的拍拆成两刀，避免长静态卡片（视觉变化太少会像 PPT）
        span = end - start
        if span > 7.0:
            mid = round(start + span * 0.55, 3)
            first, second = SPLIT_TEXT.get(beat["id"], (None, None))
            if first and second:
                cuts.append(make_cut(f"{beat['id']}_a", "text_card", start, mid, first))

                cuts.append(make_cut(f"{beat['id']}_b", "callout", mid, end, second,
                                     callout_type="tip"))
                continue
        cuts.append(make_cut(beat["id"], beat["scene"], start, end,
                             ON_SCREEN.get(beat["id"], {}).get("text"),
                             ON_SCREEN.get(beat["id"], {}).get("subtitle")))

    # ── 风格注入（三层，见 skills/07-style-control.md）──────────────
    playbook = playbook_override or style.get("playbook") or PLAYBOOK
    edit: dict = {
        "version": "1.0",
        "render_runtime": "remotion",                # 提案阶段锁定，此处不得改
        "renderer_family": "explainer-data",
        "composition_mode": "templated",
        "metadata": {"playbook": playbook, "project": PROJECT, "aspect": "9:16"},
        "cuts": cuts,
    }
    overrides = style.get("theme_overrides") or {}
    per_beat = style.get("per_beat") or {}
    if overrides:
        # 顶层 themeConfig 一旦存在，playbook 派生的主题会被**整体跳过**
        # （schema 里已补该字段，见 docs/02 第 15 条）
        edit["themeConfig"] = overrides
    for cut in cuts:                                # 每拍微调：按 id 前缀匹配
        cut.update(per_beat.get(cut["id"].split("_")[0]) or {})
    print(f"  风格：playbook={playbook}"
          + (f"，themeConfig 覆盖 {list(overrides)}" if overrides else "")
          + (f"，每拍微调 {list(per_beat)}" if per_beat else ""))
    (PDIR / "artifacts" / "edit_decisions.json").write_text(
        json.dumps(edit, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {"version": "1.0", "assets": [{
        "id": "aud_narration", "type": "audio", "path": str(audio),
        "scene_id": beats[0]["id"], "source_tool": "doubao_tts",
        "model": timing["engine"], "cost_usd": 0.0,
    }]}
    (PDIR / "artifacts" / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    packet = {
        "version": "1.0",
        "concept_options": [{
            "id": "c1", "title": "自律是环境问题", "hook": "自律，从来不是靠意志力撑出来的。",
            "narrative_structure": "misconception-first",
            "visual_approach": "全组件：标题卡 + 要点卡 + 提示框，无生成素材",
            "suggested_playbook": PLAYBOOK, "target_audience": "想养成习惯的成年人",
            "target_platform": "douyin", "target_duration_seconds": meta["target_seconds"],
            "key_points": ["意志力是消耗品", "把门槛降到不可能失败", "今晚就能做的第一步"],
            "core_message": "自律靠设计环境，不靠硬撑。",
            "cta": "挑一件小事，拆到三分钟。", "tone": "干脆、不说教",
            "grounded_in": ["research_brief"], "why_this_works": "先否定常识，再给出可立刻执行的动作。",
        }],
        "selected_concept": "c1",
        "production_plan": {
            "render_runtime": "remotion", "renderer_family": "explainer-data",
            "composition_mode": "templated", "playbook": PLAYBOOK,
            "scenes": [{"id": b["id"], "type": b["scene"], "description": b["name"]} for b in beats],
        },
        "cost_estimate": {"currency": "CNY", "total": 0.05,
                          "line_items": [{"item": "豆包配音 79 字", "cost": 0.05},
                                         {"item": "Remotion 组件渲染", "cost": 0.0}]},
        "approval": {"status": "approved", "approved_by": "user", "human_approved": True},
    }
    (PDIR / "artifacts" / "proposal_packet.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")

    out = (out_path or (PDIR / "renders" / "final.mp4")).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"  渲染中（首次会编译 Remotion，慢是正常的）…")
    result = VideoCompose().execute({
        "operation": "render",                       # 静帧/组件必须用 render
        "edit_decisions": edit,
        "asset_manifest": manifest,
        "proposal_packet": packet,
        "output_path": str(out),
        "audio_path": str(audio),
    })
    if not result.success:
        raise SystemExit(f"渲染失败：{result.error}")
    print(f"  ✅ 成片：{out}  实测 {ffprobe_duration(out):.3f}s")
    (PDIR / "artifacts" / "render_result.json").write_text(
        json.dumps(result.data or {}, ensure_ascii=False, indent=2), encoding="utf-8")
    return result.data or {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["audio", "render", "all"], default="all")
    ap.add_argument("--playbook", help="覆盖节拍表的 style.playbook（试风格用）")
    ap.add_argument("--out", help="输出 mp4 路径（试风格用）")
    args = ap.parse_args()
    meta, beats, style = load_beats()
    print(f"== {PROJECT}：{len(beats)} 拍 / 目标 {meta['target_seconds']}s ==")
    timing_path = PDIR / "artifacts" / "narration_timing.json"
    if args.stage in ("audio", "all"):
        print("-- 阶段 5a 配音 --")
        timing = stage_audio(meta, beats)
    else:
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
    if args.stage in ("render", "all"):
        print("-- 阶段 6–7 生成 artifact 并渲染 --")
        stage_render(meta, beats, timing, style,
                     playbook_override=args.playbook,
                     out_path=Path(args.out) if args.out else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
