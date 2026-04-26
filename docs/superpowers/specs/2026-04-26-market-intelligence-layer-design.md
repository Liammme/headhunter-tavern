# Market Intelligence Layer Design

日期：2026-04-26

## 背景

当前首页的 `intelligence` 更像近 14 天岗位池的即时摘要。它依赖 `jobs` 实时聚合，再把 `change_context` 和少量 `job_fact_briefs` 喂给 LLM。这个机制可以回答“今天有没有新增信号”，但很难回答“AI/Web3 招聘市场长期在发生什么变化”。

新的目标不是服务猎头、BD、赏金或认领，而是把抓取到的岗位数据作为行业观察信号源，长期沉淀 AI/Web3 市场招聘风向。

## 目标

- 建立独立的市场情报层，服务“每日情报分析”板块。
- 从岗位内容和公司招聘行为中提炼 AI/Web3 行业变化。
- 让报告能覆盖短期、中期、长期视角，而不是只讲今天新增了什么。
- 不把全量岗位或完整 JD 直接喂给 LLM。
- 让长期情报可保存、可回看、可继续累积。
- 第一阶段尽量不大改前端，只让现有情报区域展示更高质量的 `narrative`，内容较长时由前端滚动查看。

## 非目标

- 不分析 BD、猎头、客户开发、赏金、认领。
- 不把岗位来源网站作为市场信号。
- 不永久保存完整岗位链接、完整 JD、来源网站。
- 不拆成第二个物理数据库。
- 不在第一阶段做复杂事件检测或完整情报面板改版。
- 不对每条 JD 使用 LLM 单独摘要。

## 数据分层

继续使用同一个 PostgreSQL 数据库，但拆成两层生命周期不同的数据：

1. `jobs`
   - 原始岗位明细层。
   - 用于首页展示、近期调试、近期市场信号提取。
   - 可以短期保留，建议第一阶段保留 30 天。
   - 不承担长期行业记忆。

2. `market_intelligence_snapshots`
   - 市场情报沉淀层。
   - 每天从 `jobs` 中提炼一次精炼市场信号。
   - 永久保存。
   - 服务情报报告板块。

这样 `jobs` 可以自动过期清理，而长期趋势由每日快照承担。

## 快照表设计

新增表：`market_intelligence_snapshots`

建议字段：

- `id`
- `snapshot_date`
- `generated_at`
- `window_days`
- `market_signal_payload`
- `report_payload`
- `model_name`
- `status`
- `error_message`

第一阶段可每天保存一条主快照，`market_signal_payload` 内部包含 1d / 7d / 30d / 90d 多窗口信号。

## 快照保存内容

快照只保存长期分析需要的重点内容。

保存：

- 公司名
- 岗位名
- 发布日期
- 职能类别
- AI/Web3/Fintech/Infra 等领域标签
- 资深度/组织层级信号
- 技术关键词
- 业务关键词
- 市场主题归类
- 压缩 JD 摘要
- 趋势代表原因
- 多窗口统计与趋势

不保存：

- `source_name`
- `canonical_url`
- 完整 JD
- 赏金字段
- 认领字段
- BD 字段
- 爬虫来源统计

## 市场主题

第一阶段内置轻量市场主题词典，用于把岗位映射到更接近行业分析的主题，而不是只使用粗粒度岗位分类。

初始主题包括：

- AI infra
- agent / RAG
- data platform
- model deployment
- Web3 infra
- wallet / payment
- security
- risk / compliance
- trading infra
- developer tools
- enterprise AI integration

主题词典应保持可迭代，但第一版不引入外部依赖。

## 信号构建

后端先把原始岗位压缩成结构化市场信号，再把信号包交给 LLM。

信号包至少包含：

- 1d：今天发生了什么。
- 7d：短期升温、降温或反转。
- 30d：中期岗位结构和主题变化。
- 90d：长期基线和方向。
- 主题分布与变化。
- 职能结构变化。
- 资深度结构变化。
- 技术关键词升温/下降。
- 业务关键词升温/下降。
- 代表性岗位压缩样本。
- 与历史快照相比的延续、反转或新出现信号。

代表性岗位样本不保留链接，不保留来源，不保留完整 JD。样本结构示例：

```json
{
  "company": "Example AI",
  "title": "AI Infrastructure Engineer",
  "posted_date": "2026-04-26",
  "function": "工程",
  "domain": "AI infra",
  "seniority": "Senior",
  "tech_keywords": ["LLM", "RAG", "Kubernetes"],
  "business_keywords": ["enterprise deployment", "data platform"],
  "jd_summary": "负责企业级 AI 基础设施、模型部署和数据管线建设。",
  "signal_reason": "AI infra 和企业部署关键词同时出现，代表 AI 能力从实验转向工程落地。"
}
```

## LLM 输入原则

LLM 不负责发现事实，只负责基于后端整理好的事实做判断和表达。

输入不应包含：

- 全量岗位列表
- 全量 JD
- 来源网站
- 岗位链接
- 赏金
- 认领
- BD 相关字段

输入应包含：

- 多窗口市场信号。
- 主题趋势。
- 关键词趋势。
- 代表性压缩证据。
- 历史快照中的延续、反转、新出现信号。

Prompt 必须要求 LLM 回答：

1. 过去 90 天，市场大方向是什么。
2. 过去 30 天，结构有没有发生变化。
3. 最近 7 天，哪些信号在加强或反转。
4. 今天的新数据是趋势延续、短期噪声，还是新变化。

## LLM 输出结构

LLM 输出必须是 JSON。

建议结构：

```json
{
  "headline": "一句话市场判断",
  "narrative": "300-600 字市场短报",
  "primary_judgment": {
    "claim": "主线判断",
    "why_it_matters": "为什么重要",
    "confidence": "low|medium|high"
  },
  "perspectives": [
    {
      "lens": "industry",
      "judgment": "行业研究视角判断",
      "evidence": ["证据 1", "证据 2"]
    },
    {
      "lens": "product_business",
      "judgment": "产品/业务视角判断",
      "evidence": ["证据 1", "证据 2"]
    },
    {
      "lens": "organization_hiring",
      "judgment": "组织招聘视角判断",
      "evidence": ["证据 1", "证据 2"]
    }
  ],
  "trend_cards": [
    {
      "title": "AI infra 持续升温",
      "direction": "rising|cooling|shifting|stable|emerging",
      "time_horizon": "7d|30d|90d",
      "judgment": "趋势判断",
      "evidence": ["证据 1", "证据 2"],
      "confidence": "low|medium|high"
    }
  ],
  "watchlist": [
    "接下来继续观察什么信号。"
  ]
}
```

第一阶段前端只展示 `narrative`。其他结构化字段先保存，为后续趋势卡片和观察点 UI 做准备。

## 报告风格

报告应兼具行业研究、产品/业务、组织招聘三个视角，但必须有主次。

输出优先级：

1. 一个主线判断。
2. 行业研究视角：行业资源流向、赛道升温/降温、AI/Web3 交叉点。
3. 产品/业务视角：公司在补研究、平台、交付、风控、合规、运营还是增长能力。
4. 组织招聘视角：公司是在探索新方向、搭核心团队，还是规模化交付。
5. 后续观察点：后续需要继续验证哪些信号。

风格要求：

- 直接、克制、有判断。
- 像产业研究简报，而不是销售话术。
- 不要鸡血，不要泛泛建议。
- 不要把统计数字机械复述成报告。
- 不要平均用力，必须突出证据最强的主线。

## 质量约束

后端应校验 LLM 输出，不合格时重写或降级。

约束包括：

- 输出必须是合法 JSON。
- `narrative` 建议 300-600 字。
- 必须至少包含 30d 或 90d 长期视角。
- 必须包含一个主线判断。
- `perspectives` 至少覆盖 industry、product_business、organization_hiring。
- `trend_cards` 最多 4 张。
- `watchlist` 3 条以内。
- `confidence` 只能是 `low`、`medium`、`high`。
- 禁止出现 BD、猎头、赏金、认领、客户开发等表达。
- 禁止出现岗位来源网站作为市场判断依据。
- 禁止引用输入中不存在的公司、岗位、主题。
- 禁止“根据数据分析可得”“综合来看”“建议持续关注”等空泛报告腔。

## 生成时机与读取方式

每日任务 `daily_bounty` 完成后：

1. 抓取岗位。
2. 写入/更新 `jobs`。
3. 生成市场信号包。
4. 调用 LLM 生成报告。
5. 写入 `market_intelligence_snapshots`。

首页读取：

- 优先读取最新成功的 `market_intelligence_snapshots.report_payload.narrative`。
- 如果当天快照失败，读取上一份成功快照。
- 如果没有任何成功快照，再降级到现有规则逻辑。

## 前端第一阶段

第一阶段不做完整情报面板。

保留现有情报展示区域：

- 继续展示 `narrative`。
- 如果内容变长，情报区域内部支持滚动。
- 后端返回的结构化字段先保存，后续再做趋势卡片、证据摘要、观察点 UI。

## 数据保留策略

- `jobs`：第一阶段建议保留 30 天。
- `market_intelligence_snapshots`：永久保存。

如果情报层稳定后，`jobs` 可以继续保持短期窗口。长期趋势依赖快照累计，而不是依赖完整岗位明细永久存在。

## 验证标准

后端验证：

- 能生成市场快照。
- 快照不包含来源、链接、完整 JD、赏金、认领、BD。
- LLM 输入不包含全量岗位。
- LLM 输出通过 JSON schema 和内容约束。
- `daily_bounty` 结束后写入快照。
- 首页能读取最新成功快照。

产品验证：

- 报告能讲清 AI/Web3 市场主线变化。
- 报告包含 30d/90d 长期视角。
- 报告能区分短期噪声和中长期趋势。
- 报告不出现 BD、赏金、认领、来源网站。
- 报告不只是统计复述。

## 实施边界

第一阶段只做后端情报层和最小前端滚动适配。完整趋势卡片 UI、复杂事件检测、主题词典后台管理、历史报告页面都留到后续阶段。
