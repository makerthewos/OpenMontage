# One-click OpenMontage workflow

## 1. Discover, preflight, and resume

1. Read `AGENT_GUIDE.md` and inspect the user's inputs.
2. Resolve paths with `rg --files` or targeted directory listings. Do not ask for
   information available in the workspace.
3. Look for a matching project and call `get_next_stage()` before initialization.
   Resume valid completed, awaiting-human, or in-progress checkpoints.
4. Run `provider_menu_summary()`, inspect runtime warnings, and inspect
   `video_compose` render-engine availability.
5. Complete the one-shot intake and persist `artifacts/intake_brief.md`.

For a new run, derive a kebab-case project ID, call `init_project()` with the
selected pipeline, and open the Backlot board. Board launch failure is non-fatal.

## 2. Select the pipeline

Use the narrowest pipeline that matches the source and promised outcome:

| Signal | Pipeline |
|---|---|
| Topic, article, report, educational idea | `animated-explainer` |
| Trailer, teaser, cinematic mood, generated shots | `cinematic` |
| Motion graphics or animation-led story | `animation` |
| Reusable rigged character performance | `character-animation` |
| Recorded presenter is primary | `talking-head` |
| Source footage plus generated support visuals | `hybrid` |
| App, browser, terminal, product walkthrough | `screen-demo` |
| Many clips from one long recording | `clip-factory` |
| Podcast highlights | `podcast-repurpose` |
| AI presenter or lip-sync host | `avatar-spokesperson` |
| Translate, subtitle, or dub an existing video | `localization-dub` |

Read the chosen manifest completely. Check required and fallback tools against
the live registry and report preflight as passed, degraded, or blocked. Explain
beta status where applicable.

## 3. Analyze sources and references

For reference videos, read `skills/meta/video-reference-analyst.md`, then produce
the required structured analysis from transcript, scene detection, motion
classification, sampled frames, and direct visual inspection. Preserve the five
visual aspects. Extract principles rather than copyrighted media or wording.

For source-footage pipelines, review duration, codecs, orientation, audio,
speaker continuity, usable segments, privacy-sensitive material, and edit risks.
For topic-led work, run the manifest's research stage and ground factual claims
in appropriate sources. Keep facts, user claims, and creative inference distinct.

## 4. Proposal and decisions

Read the selected proposal/idea director plus the taste, runtime, and checkpoint
skills it requires. Present differentiated concepts when the brief is open, and
lock decisions for pipeline, concept, provider/model, render runtime, authoring
mode, visual identity, voice, subtitles, music, motion treatment, budget, output
variants, and approval policy.

When both Remotion and HyperFrames are available, both must appear in the
runtime decision with brief-specific tradeoffs. Revisions append a new decision
using the same `(category, subject)` pair; never rewrite decision history.

## 5. Samples and gated production

Before a paid or batch run, generate every sample required by the chosen
manifest/director: reference-style preview, TTS performance sample, representative
image/video asset, avatar, character action, or music cue. Use the intended final
provider, model, voice, runtime, and settings.

- With staged review, write `awaiting_human`, present the sample and costs, then
  end the turn.
- With explicit full-run preauthorization, cite the recorded `approval_policy`,
  self-review the sample, and continue only when it passes inside the authorized
  scope.
- A failed sample or material deviation always stops production.

Run the remaining manifest stages serially. Read each stage director and every
selected generation tool's Layer 3 skill before executing. Announce provider,
model or voice, reason, cost, and sample/batch status before consequential calls.
Update in-progress checkpoints during long work and write canonical artifacts to
the project directory.

At the assets gate, provide scene-by-scene assets or representative review stills.
Do not render a full draft merely to create an approval surface when the protocol
requires asset review first.

## 6. Compose, verify, and deliver

Carry the approved runtime unchanged into edit and compose. Build subtitles from
measured narration or source timing. Apply the approved music and ducking plan;
when no music was selected, verify that none was introduced.

Render through the manifest-approved composition tool and validate:

- expected container, codecs, stream count, frame rate, dimensions, and duration;
- clean full decode with no black, missing, corrupt, or broken frames;
- readable text and captions inside platform safe areas;
- narration clarity, music balance, no clipping, and A/V synchronization;
- sampled frames at the opening, middle, transitions, and ending;
- provider, model, runtime, output variants, and actual cost match the decision log.

Write `render_report` and `final_review`. Give the user clickable absolute paths
to deliverables and report format, duration, language, audio treatment, actual
cost, and remaining limitations.

Publishing is a separate external action. Perform it only when the consolidated
intake or a later explicit user instruction names the destination and authorizes
publishing.

## Stop conditions

Stop and group all blockers into one message when required input cannot be
accessed, the selected provider/runtime is unavailable, a fallback changes the
approved result, additional spend exceeds the ceiling, a critical review issue
survives two repair rounds, or external publishing lacks explicit authorization.
