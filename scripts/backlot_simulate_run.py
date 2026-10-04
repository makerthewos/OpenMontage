"""Simulate a pipeline run on disk to exercise the Backlot live board.

Drives a fake production through the REAL contract — init_project,
in_progress checkpoints, gated awaiting_human states, tool events,
progressively-written artifacts — so the board can be watched updating live.
Also useful as a demo driver.

    python scripts/backlot_simulate_run.py [--project backlot-demo-run]
        [--fast] [--cleanup]

--fast     compresses waits to ~0.3s (for automated verification)
--cleanup  removes the project directory at the end
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.checkpoint import PROJECTS_DIR, init_project, write_checkpoint
from lib.events import emit_event

SCENES = [
    ("sc1", "Opening — a lighthouse at dusk", 0, 4, "The coast holds its breath."),
    ("sc2", "The beam sweeps the water", 4, 9, "Every night, the same promise."),
    ("sc3", "A storm builds offshore", 9, 15, "Until the night the light went out."),
    ("sc4", "The keeper climbs the stairs", 15, 21, "Someone still has to climb."),
]


def artifacts_for(project_id: str) -> dict:
    script = {
        "version": "1.0",
        "title": "The Last Lighthouse",
        "total_duration_seconds": 21,
        "sections": [
            {"id": f"s{i+1}", "label": desc.split("—")[0].strip(), "text": narration,
             "start_seconds": s0, "end_seconds": s1}
            for i, (sid, desc, s0, s1, narration) in enumerate(SCENES)
        ],
    }
    scene_plan = {
        "version": "1.0",
        "scenes": [
            {"id": sid, "type": "generated", "description": desc,
             "start_seconds": s0, "end_seconds": s1,
             "script_section_id": f"s{i+1}",
             "hero_moment": sid == "sc3",
             "required_assets": [{"type": "image", "description": desc, "source": "generate"}]}
            for i, (sid, desc, s0, s1, _n) in enumerate(SCENES)
        ],
    }
    return {"script": script, "scene_plan": scene_plan}


def proposal_artifacts() -> dict:
    """Schema-valid proposal_packet + decision_log for the board demo.

    `write_checkpoint` refuses to advance a stage until every earlier stage is
    'completed', so the simulation has to produce a real proposal checkpoint
    before it can touch script. These fixtures satisfy
    schemas/artifacts/proposal_packet.schema.json (>=3 concept options) and
    schemas/artifacts/decision_log.schema.json.
    """
    concepts = [
        {
            "id": "c1", "title": "The Last Lighthouse",
            "hook": "Every night for forty years, the same beam. Then it stopped.",
            "narrative_structure": "story",
            "visual_approach": "Moody dusk photography, slow push-ins, storm-lit silhouettes",
            "suggested_playbook": "clean-professional",
            "target_audience": "General documentary audience",
            "target_platform": "youtube",
            "target_duration_seconds": 21,
            "key_points": ["Routine read as devotion", "The night the light failed",
                           "Someone still climbs"],
            "core_message": "Care persists quietly, long after anyone is watching.",
            "cta": "Watch to the end.",
            "tone": "Elegiac, restrained",
            "grounded_in": ["research_brief"],
            "why_this_works": "One concrete object carries an abstract idea about duty.",
        },
        {
            "id": "c2", "title": "Forty Years of Light",
            "hook": "The keepers are gone. The light is not.",
            "narrative_structure": "timeline",
            "visual_approach": "Archival-style stills, time-lapse coastline",
            "suggested_playbook": "clean-professional",
            "target_audience": "History enthusiasts",
            "target_platform": "youtube",
            "target_duration_seconds": 21,
            "key_points": ["Automation arrives", "What is lost", "What remains"],
            "core_message": "Automation changes labour, not meaning.",
            "cta": "Follow for more.",
            "tone": "Reflective",
            "grounded_in": ["research_brief"],
            "why_this_works": "A timeline makes an invisible transition legible.",
        },
        {
            "id": "c3", "title": "What the Beam Cannot See",
            "hook": "The lighthouse guards the coast. Who guards the lighthouse?",
            "narrative_structure": "myth_busting",
            "visual_approach": "Interior tower details, rope and brass, rain on glass",
            "suggested_playbook": "clean-professional",
            "target_audience": "Viewers who like quiet craft stories",
            "target_platform": "youtube",
            "target_duration_seconds": 21,
            "key_points": ["The myth of the solitary keeper", "Maintenance as heroism",
                           "The climb nobody films"],
            "core_message": "The unglamorous upkeep is the real story.",
            "cta": "Share this with someone who keeps things running.",
            "tone": "Intimate, tactile",
            "grounded_in": ["research_brief"],
            "why_this_works": "Reframes a familiar symbol around unseen labour.",
        },
    ]

    proposal_packet = {
        "version": "1.0",
        "concept_options": concepts,
        "selected_concept": {
            "concept_id": "c1",
            "rationale": "Strongest single-image hook and the most compact emotional arc for 21 seconds.",
            "modifications": [],
        },
        "production_plan": {
            "pipeline": "cinematic",
            "playbook": "clean-professional",
            "render_runtime": "remotion",
            "stages": [
                {"stage": "script", "approach": "Four-beat narration, 21s total.",
                 "tools": [{"tool_name": "local", "role": "Draft narration beats",
                            "available": True}]},
                {"stage": "scene_plan", "approach": "One shot per beat, hero moment on the storm.",
                 "tools": [{"tool_name": "local", "role": "Lay out shots and timings",
                            "available": True}]},
                {"stage": "assets", "approach": "Generate one image per scene.",
                 "fallback_if_unavailable": "Archive.org stills",
                 "tools": [{"tool_name": "flux_image", "role": "Generate scene stills",
                            "provider": "fal", "available": False,
                            "estimated_cost_usd": 0.2,
                            "why_this_provider": "Cost-effective per-image quality for a photographic look"}]},
                {"stage": "edit", "approach": "Cross-dissolves, 4-9s per shot.",
                 "tools": [{"tool_name": "ffmpeg", "role": "Assemble timeline",
                            "available": True}]},
                {"stage": "compose", "approach": "Render at 1920x1080/30.",
                 "tools": [{"tool_name": "video_compose", "role": "Final render",
                            "provider": "remotion", "available": True}]},
            ],
        },
        "cost_estimate": {
            "total_estimated_usd": 0.2,
            "line_items": [
                {"tool": "flux_image", "operation": "Generate 4 scene images",
                 "quantity": 4, "estimated_usd": 0.2, "notes": "0.05 per image"},
            ],
            "budget_verdict": "within_budget",
        },
        "approval": {
            "status": "approved",
            "user_notes": "Approved for the local board demo.",
            "approved_budget_usd": 5.0,
        },
    }

    decision_log = {
        "version": "1.0",
        "project_id": "backlot-demo-run",
        "decisions": [
            {
                "decision_id": "d-001", "stage": "proposal",
                "category": "pipeline_selection", "subject": "Pipeline for a 21s elegiac short",
                "options_considered": [
                    {"option_id": "cinematic", "label": "cinematic", "score": 0.9,
                     "reason": "Photographic pacing and a single hero moment fit the concept."},
                    {"option_id": "documentary-montage", "label": "documentary-montage",
                     "score": 0.6, "reason": "Strong for found footage, weaker for a scripted beat.",
                     "rejected_because": "Needs a real-footage library this demo does not have."},
                    {"option_id": "animated-explainer", "label": "animated-explainer",
                     "score": 0.4, "reason": "Explainer grammar would fight the elegiac tone.",
                     "rejected_because": "Tone mismatch."},
                ],
                "selected": "cinematic",
                "reason": "Photographic pacing and a single hero moment fit the concept; no overlay narration required.",
            },
            {
                "decision_id": "d-002", "stage": "proposal",
                "category": "concept_selection", "subject": "Concept direction",
                "options_considered": [
                    {"option_id": "c1", "label": "The Last Lighthouse", "score": 0.88,
                     "reason": "Most compact emotional arc and the strongest first-frame hook."},
                    {"option_id": "c2", "label": "Forty Years of Light", "score": 0.71,
                     "reason": "Clear structure, but the timeline dilutes the single-image hook.",
                     "rejected_because": "Less immediate in the first two seconds."},
                    {"option_id": "c3", "label": "What the Beam Cannot See", "score": 0.74,
                     "reason": "Fresh angle on unseen labour; slightly more abstract open.",
                     "rejected_because": "Harder to land in 21 seconds."},
                ],
                "selected": "c1",
                "reason": "Strongest hook-to-payoff ratio at this duration.",
            },
            {
                "decision_id": "d-003", "stage": "proposal",
                "category": "render_runtime_selection", "subject": "Composition runtime",
                "options_considered": [
                    {"option_id": "remotion", "label": "Remotion", "score": 0.86,
                     "reason": "Scene components give controlled typography and transitions."},
                    {"option_id": "hyperframes", "label": "HyperFrames", "score": 0.7,
                     "reason": "Great for HTML/GSAP motion, more setup than this cut needs.",
                     "rejected_because": "No motion-heavy sequences planned."},
                    {"option_id": "ffmpeg", "label": "FFmpeg", "score": 0.45,
                     "reason": "Enough for concat/trim only.",
                     "rejected_because": "Cannot author the title and transition treatment."},
                ],
                "selected": "remotion",
                "reason": "Delivers the intended title and transition treatment at 1920x1080/30.",
            },
        ],
    }

    return {"proposal_packet": proposal_packet, "decision_log": decision_log}


def edit_decisions_artifact() -> dict:
    """Schema-valid edit_decisions covering the full planned runtime."""
    returns = {"remotion": "CinematicRenderer"}
    return {
        "version": "1.0",
        "render_runtime": "remotion",
        "renderer_family": "cinematic-trailer",
        "composition_mode": "templated",
        "cuts": [
            {
                "id": f"cut_{i + 1}", "source": f"img_{sid}", "layer": "primary",
                "in_seconds": 0, "out_seconds": round(s1 - s0, 2), "speed": 1.0,
                "transform": {"scale": 1.0, "position": "center",
                              "animation": "ken-burns-slow-zoom"},
            }
            for i, (sid, _desc, s0, s1, _n) in enumerate(SCENES)
        ],
        "transitions": [
            {"type": "cross-dissolve", "at_seconds": s1, "duration_seconds": 0.6}
            for (_sid, _desc, _s0, s1, _n) in SCENES[:-1]
        ],
        "metadata": {"edit_note": returns["remotion"], "total_duration_seconds": 21},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default="backlot-demo-run")
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()

    wait = 0.3 if args.fast else 2.5
    pid = args.project
    pdir = PROJECTS_DIR / pid
    if pdir.exists():
        shutil.rmtree(pdir)

    print(f"[sim] init_project {pid}")
    init_project(pid, title="The Last Lighthouse", pipeline_type="cinematic",
                 style_playbook="clean-professional")
    art = artifacts_for(pid)

    def save_artifact(name: str, data: dict) -> None:
        path = pdir / "artifacts" / f"{name}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def cp(stage: str, status: str, artifacts: dict, **kw) -> None:
        write_checkpoint(PROJECTS_DIR, pid, stage, status, artifacts,
                         pipeline_type="cinematic", **kw)
        print(f"[sim] checkpoint {stage} -> {status}")
        time.sleep(wait)

    # research auto-proceeds (schema-valid fixture from the contract tests)
    cp("research", "in_progress", {})
    from tests.contracts.test_phase0_contracts import sample_artifact
    brief = sample_artifact("research_brief")
    brief["topic"] = "The Last Lighthouse"
    cp("research", "completed", {"research_brief": brief})

    # proposal auto-proceeds, but the checkpoint must exist: write_checkpoint
    # enforces that every earlier stage is 'completed' before a later stage may
    # advance, so skipping proposal here aborts the whole simulation.
    cp("proposal", "in_progress", {})
    proposal_art = proposal_artifacts()
    save_artifact("proposal_packet", proposal_art["proposal_packet"])
    save_artifact("decision_log", proposal_art["decision_log"])
    cp("proposal", "awaiting_human", {
        "proposal_packet": proposal_art["proposal_packet"],
        "decision_log": proposal_art["decision_log"],
    })
    time.sleep(wait)  # "user picks a concept on the board"
    cp("proposal", "completed", {
        "proposal_packet": proposal_art["proposal_packet"],
        "decision_log": proposal_art["decision_log"],
    }, human_approved=True)

    # script gates: awaiting_human -> approved
    cp("script", "in_progress", {})
    save_artifact("script", art["script"])
    cp("script", "awaiting_human", {"script": art["script"]},
       review={"round": 1, "decision": "pass", "critical": 0, "suggestions": 1,
               "nitpicks": 0, "summary": "Hook is strong; tightened s3."})
    time.sleep(wait)  # "user reads the script on the board"
    cp("script", "completed", {"script": art["script"]}, human_approved=True)

    # scene_plan gates too
    cp("scene_plan", "in_progress", {})
    save_artifact("scene_plan", art["scene_plan"])
    cp("scene_plan", "awaiting_human", {"scene_plan": art["scene_plan"]})
    time.sleep(wait)
    cp("scene_plan", "completed", {"scene_plan": art["scene_plan"]}, human_approved=True)

    # assets: per-scene tool events + growing manifest + partial progress
    cp("assets", "in_progress", {})
    manifest = {"version": "1.0", "assets": [], "total_cost_usd": 0.0}
    done_ids = []
    from PIL import Image, ImageDraw
    palette = [(24, 32, 48), (40, 30, 60), (60, 24, 24), (20, 48, 40)]
    for i, (sid, desc, _s0, _s1, _n) in enumerate(SCENES):
        emit_event(pdir, {"tool": "flux_image", "event": "start", "scene_id": sid})
        print(f"[sim] generating {sid}…")
        time.sleep(wait * 1.5)
        rel = f"assets/images/{sid}.png"
        img = Image.new("RGB", (640, 360), palette[i % 4])
        draw = ImageDraw.Draw(img)
        draw.text((20, 160), f"{sid} — {desc[:40]}", fill=(230, 225, 210))
        img.save(pdir / rel)
        emit_event(pdir, {"tool": "flux_image", "event": "finish", "scene_id": sid,
                          "success": True, "cost_usd": 0.05, "duration_s": wait * 1.5,
                          "output_path": rel})
        manifest["assets"].append({
            "id": f"img_{sid}", "type": "image", "path": rel, "scene_id": sid,
            "source_tool": "flux_image", "model": "flux-sim", "cost_usd": 0.05,
            "prompt": desc, "quality_score": 0.88,
        })
        manifest["total_cost_usd"] = round(manifest["total_cost_usd"] + 0.05, 2)
        save_artifact("asset_manifest", manifest)
        done_ids.append(sid)
        write_checkpoint(PROJECTS_DIR, pid, "assets", "in_progress", {},
                         pipeline_type="cinematic",
                         metadata={"partial_progress": {"completed_scene_ids": done_ids}},
                         cost_snapshot={"total_spent_usd": manifest["total_cost_usd"],
                                        "total_reserved_usd": 0.0,
                                        "budget_remaining_usd": 5 - manifest["total_cost_usd"]})
    # assets gate (the storyboard review)
    cp("assets", "awaiting_human", {"asset_manifest": manifest},
       cost_snapshot={"total_spent_usd": manifest["total_cost_usd"],
                      "total_reserved_usd": 0.0,
                      "budget_remaining_usd": 5 - manifest["total_cost_usd"]})
    time.sleep(wait)
    cp("assets", "completed", {"asset_manifest": manifest}, human_approved=True)

    # edit auto-proceeds (human_approval_default: false) — closes the loop so the
    # board shows a finished cut rather than stopping mid-pipeline.
    cp("edit", "in_progress", {})
    edit_art = edit_decisions_artifact()
    save_artifact("edit_decisions", edit_art)
    cp("edit", "completed", {"edit_decisions": edit_art})

    print(f"[sim] done — board at http://127.0.0.1:4750/p/{pid}")
    if args.cleanup:
        shutil.rmtree(pdir)
        print("[sim] cleaned up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
