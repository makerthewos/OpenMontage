---
name: one-click-video-generator
description: >
  Run OpenMontage end to end from one consolidated video brief: inspect source
  media and references, select the appropriate pipeline, research and plan,
  generate narration and visuals, compose, review, and deliver a verified video.
  Use when the user asks for one-click video generation or a complete video
  production workflow. Routes among explainer, cinematic, animation, footage-led,
  screen-demo, clipping, avatar, and localization pipelines. Not for an isolated
  image, audio, or single post-production operation.
metadata:
  tags: "openmontage, one-click-video, video-production, pipeline-router, generation"
---

# One-click Video Generator

Convert one user brief into a finished video while preserving OpenMontage's
pipeline, provider, budget, review, and checkpoint contracts. “One click” means
one consolidated intake and automated routing; it does not mean bypassing
quality gates or silently changing the approved production path.

## Start here

Work from the OpenMontage repository root and read `AGENT_GUIDE.md` completely
before responding to the production request. Perform read-only discovery first:

1. Inspect supplied URLs, local paths, source media, scripts, and existing
   project checkpoints.
2. Run `provider_menu_summary()` and inspect `video_compose` render engines.
3. Read [references/intake.md](references/intake.md), then ask every unresolved
   requirement in one consolidated message. Do not repeat facts already given.
4. Persist `projects/<project-id>/artifacts/intake_brief.md`, marking each field
   as `stated`, `accepted_default`, `inferred_from_source`, or `not_applicable`.
5. Read [references/workflow.md](references/workflow.md), select the pipeline,
   and execute its manifest and director skills stage by stage.

If the user supplies enough information in the first message, skip the form.
When the form is needed, a reply such as “主题是 X，其余默认，全程预授权”
explicitly accepts every displayed default.

Ask another question only when production is blocked by inaccessible required
material, contradictory instructions, an ambiguous deliverable, or a material
change to the approved provider, model, runtime, voice, music plan, motion
treatment, budget, or publishing destination. Group all blockers into one
message.

## Routing rules

Select the pipeline from the user's actual inputs and outcome:

- Topic, idea, report, article, or educational script → `animated-explainer`.
- Trailer, teaser, atmosphere-led or generated-shot piece → `cinematic`.
- Motion-design-first piece → `animation`; reusable acting character →
  `character-animation`.
- Recorded speaker footage → `talking-head`; source footage plus generated
  support visuals → `hybrid`.
- App, browser, terminal, or product walkthrough → `screen-demo`.
- Many short clips from one long video → `clip-factory`; podcast highlights →
  `podcast-repurpose`.
- AI presenter or lip-sync host → `avatar-spokesperson`.
- Translation, subtitles, or dubbing of an existing video → `localization-dub`.

If two routes remain plausible, recommend one in the consolidated intake with
the practical tradeoff. Beta pipelines must be labeled beta.

## Non-negotiable production rules

- Use the selected pipeline manifest as the source of truth. Read the named
  stage director before each stage and the selected tool's Layer 3 skill before
  generation.
- Analyze every reference video through
  `skills/meta/video-reference-analyst.md`. Extract reusable grammar; do not copy
  footage, audio, watermark, wording, or distinctive assets.
- Present the real capability menu, provider/model choices, music plan, cost,
  render runtimes, and authoring mode before locking decisions.
- When both Remotion and HyperFrames are available, show both with brief-specific
  fit and tradeoffs. Never silently default.
- Produce representative samples before paid or batch generation when the
  manifest or director requires them.
- Keep all generated artifacts under `projects/<project-id>/`, resume valid
  checkpoints, and maintain the append-only decision log.
- Never substitute provider, model, runtime, voice, music, real motion, or a
  paid path without approval that covers the change.
- External publishing is performed only when the user explicitly includes it.

## Approval policy

Offer standard staged review and explicit full-run preauthorization in the
one-shot form. If the user chooses full-run preauthorization, record the exact
answer in `decision_log` with category `approval_policy` and cite that decision
as approval evidence at every covered gate. Its scope is limited to the resolved
brief, provider/model shortlist, runtime, authoring mode, music choice, delivery
targets, and budget ceiling.

Stop despite preauthorization when a material choice changes, a paid cost would
exceed the ceiling, a required sample fails, or a critical review issue remains.
Without explicit full-run preauthorization, use normal gated checkpoints and end
the turn whenever the manifest requires human approval.

## Completion standard

Deliver the requested video files plus captions, audio, canonical artifacts, and
render report. Verify the actual output with probe/decode checks and sampled-frame
review. Confirm dimensions, duration, frame rate, readable safe-area text,
narration and music state, A/V synchronization, and absence of black, missing,
or broken frames.

Before reporting success, score source fidelity, narrative clarity, visual
continuity, motion quality, caption readability, audio quality, and technical
validity from 1 to 5. Repair any score below 4 or report the remaining limitation.
