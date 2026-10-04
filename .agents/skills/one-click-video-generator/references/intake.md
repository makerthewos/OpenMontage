# One-shot video intake

Use this form only after inspecting supplied material and querying the live tool
registry. Remove fields the user already answered, but place every unresolved
choice in the same message. Replace provider and runtime labels with capabilities
actually available on the machine.

The only universally required input is what the video is about or which source
material it should transform. All other fields may use clearly displayed
defaults. Do not ask the user to choose implementation details that can be
derived from their goal, media, and the registry.

## Consolidated question

If the platform's structured question UI cannot show the complete form in one
prompt, send one plain-text fill-in block:

```text
请一次回复这份视频制作单。最简回复可以是：
“主题/素材是 ___，其余全部默认，按【逐阶段审阅 / 全程预授权】执行。”

1. 内容与目的【必填】
   - 主题、标题、脚本、文章、产品、网页或原始视频：
   - 视频用途：讲解 / 宣传 / 记录 / 娱乐 / 教程 / 剪辑分发 / 自动推荐
   - 希望观众看完理解、感受或执行什么：

2. 输入材料【默认：允许基于公开资料研究并原创制作】
   - 本地文件、文件夹、网页、文档、音视频或素材路径：
   - 指定事实来源、必须使用的自有素材或禁止使用的内容：

3. 受众【默认：普通中文互联网用户】
   - 年龄、知识水平、使用场景或目标客户：

4. 成片规格【默认：单条中文短视频，9:16，1080×1920，60–90 秒】
   - 发布平台：抖音 / 小红书 / 视频号 / B站 / YouTube / 网站 / 内部使用
   - 时长、画幅、分辨率、数量、语言或截止时间：

5. 风格与参考【默认：根据内容设计原创视觉】
   - 参考视频链接、本地视频或参考素材文件夹：
   - 喜欢参考中的什么；明确不想要什么：
   - 真实感、动画感、节奏、颜色或品牌风格要求：

6. 声音【默认：当前可用的中文旁白、完整字幕；音乐从免费来源自动推荐，不匹配则不用】
   - 旁白：男声 / 女声 / 指定声音 / 多角色 / 无旁白
   - 音频结构：单旁白 / 人物对白 / 旁白加人物 / 保留原声
   - 字幕：完整 / 精简关键词 / 双语 / 关闭
   - 音乐：自动推荐 / 无 / 自带文件 / 免费曲库 / 允许付费生成

7. 制作路线【由项目根据输入推荐，并列出真实可用选项】
   - 内容路线：全生成 / 使用原始素材剪辑 / 原素材加生成画面 / 数字人 / 翻译配音
   - 合成引擎：Remotion / HyperFrames / 其他实际可用路线
   - 作者模式：Atelier 定制 / Templated 模板
   - 如果接受项目推荐，可写“自动选择推荐项”：

8. 品牌与交付【默认：无 Logo、无强营销 CTA，仅交付成片和字幕】
   - Logo、字体、署名、账号名、固定口播、CTA、封面或多版本要求：
   - 是否需要发布到外部平台；如需要，请写明平台：

9. 预算【默认：新增素材与生成 API 预算 0 元，优先免费或本地能力】
   - 可接受的最高新增 API 花费：

10. 审阅授权【二选一】
   - 逐阶段审阅：按管线规定，在提案、样片、脚本、分镜或素材节点等我确认。
   - 全程预授权：在本制作单、推荐供应商/模型、合成方式和预算内自动采用推荐方案并连续完成；把本回答记录为 approval_policy。任何超预算、供应商替换、发布行为或重大风格变化仍须先问我。
```

## Dynamic options and defaults

- Run preflight before showing item 7. If both Remotion and HyperFrames are
  available, describe both with one brief-specific strength and one tradeoff,
  then mark one recommendation. “自动选择推荐项” is explicit approval of that
  displayed recommendation.
- List only providers found through the registry. Do not hardcode credential
  setup or claim a provider is available from memory.
- Adapt the default duration and aspect ratio when the user already named a
  platform. Platform-specific defaults override the generic 9:16, 60–90 second
  default.
- For source-footage requests, preserve source language and original audio by
  default unless the requested outcome requires narration, dubbing, or replacement.
- For batch output, default to templated mode; for one hero deliverable, recommend
  Atelier when the budget and schedule permit.

## After the answer

Summarize the resolved brief in one compact paragraph. Do not turn the summary
into another approval question when the user selected full-run preauthorization.
Persist exact wording for budget, external publishing, and approval policy.

Unfilled optional fields use only defaults displayed to the user. If required
material is inaccessible or the request is contradictory, group all remaining
blockers into one follow-up instead of restarting a serial interview.
