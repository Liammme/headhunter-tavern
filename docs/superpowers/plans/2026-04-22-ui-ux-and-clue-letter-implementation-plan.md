# UI/UX 重构与单公司线索来信 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把首页重构成“情报封面 + 公司猎单池”，同时上线单公司 `侦查线索` 来信能力，并完成公司级认领与预计赏金的交互语义切换。

**Architecture:** 本阶段分两条主线并行推进，但执行顺序上必须先收拢公司级语义和首页信息架构，再叠加视觉系统和单公司来信功能。前端只消费稳定的首页和公司卡数据；单公司线索来信走独立的后端生成链路，不反向污染首页主链。

**Tech Stack:** Next.js App Router、React、TypeScript、FastAPI、现有 LLM intelligence 服务、现有公司聚合与评分 v2 主链。

---

## 文件边界

### 前端主文件

- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\app\page.tsx`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\app\globals.css`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyDaySection.tsx`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyCard.tsx`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\IntelligencePanel.tsx`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\lib\types.ts`

### 后端主文件

- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\home_feed.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\home_feed_aggregation.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\feed_snapshot.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\intelligence.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\job_enrichment.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\schemas\home.py`

### 需要新增的文件（建议）

- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyClaimSeal.tsx`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyClueLetter.tsx`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyClueTrigger.tsx`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\company_clue_letter.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\schemas\company_clue.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\api\company_clue.py`

### 重点测试文件

- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_home_api.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_home_feed_aggregation.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_intelligence.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_claim_service.py`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyCard.test.tsx`
- `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\IntelligencePanel.test.tsx`（如不存在则新增）

---

## Phase 1：公司级语义先收口

### Task 1: 明确首页和公司卡的公司级契约

**Files:**
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\schemas\home.py`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\feed_snapshot.py`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\lib\types.ts`
- Test: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_home_api.py`

- [ ] Step 1: 给公司卡 schema 补齐公司级认领与预计赏金字段草案  
字段至少要有：
  - `claimed_by`
  - `claim_status`
  - `estimated_bounty_amount`
  - `estimated_bounty_label`
  - `company_url`

- [ ] Step 2: 跑 home API 测试，确认新增字段前测试基线  
Run: `pytest F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_home_api.py -q`

- [ ] Step 3: 最小实现这些字段的可选输出，先允许为 `null` / 默认值  
要求：不破坏现有 `/api/v1/home` 契约，只做加性字段。

- [ ] Step 4: 重新跑 home API 测试并补断言  
Run: `pytest F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_home_api.py -q`

- [ ] Step 5: Commit  
`git commit -m "refactor: add company-level home card fields"`

### Task 2: 把岗位级认领语义切换为公司级认领语义

**Files:**
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\home_feed_aggregation.py`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\claim_service.py`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\api\claims.py`
- Test: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_claim_service.py`
- Test: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_home_feed_aggregation.py`

- [ ] Step 1: 写失败测试，表达“同一家公司只能被认领一次”  
- [ ] Step 2: 跑测试确认失败  
Run: `pytest F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_claim_service.py -q`

- [ ] Step 3: 在服务层实现公司级独占认领  
要求：按公司归并，而不是按岗位归并；不得修改前端 API 结构之外的逻辑。

- [ ] Step 4: 在聚合层改成输出公司级认领状态  
要求：岗位行不再承担认领状态主语。

- [ ] Step 5: 跑聚合与 claim 回归  
Run: `pytest F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_claim_service.py F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_home_feed_aggregation.py -q`

- [ ] Step 6: Commit  
`git commit -m "feat: switch claim semantics to company level"`

---

## Phase 2：首页情报封面重构

### Task 3: 首屏信息架构重排为“主纸页 + 注记栏 + 榜单露头”

**Files:**
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\app\page.tsx`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\IntelligencePanel.tsx`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\app\globals.css`
- Test: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\IntelligencePanel.test.tsx`

- [ ] Step 1: 先写一个最小组件测试或快照，约束首屏出现主情报区和右侧注记区  
- [ ] Step 2: 跑测试确认失败  
- [ ] Step 3: 调整 `page.tsx` 与 `IntelligencePanel.tsx`，把首屏改成双区块布局  
- [ ] Step 4: 在 `globals.css` 中先完成骨架样式，不急着做完整纸张细节  
- [ ] Step 5: 跑前端构建验证首屏不崩  
Run: `cd F:\赏金猎人\.worktrees\bounty-pool-v1\frontend; npm run build`

- [ ] Step 6: Commit  
`git commit -m "feat: restructure homepage hero into intelligence cover"`

### Task 4: 落手绘档案视觉系统，但只覆盖首屏和公司卡

**Files:**
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\app\globals.css`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\IntelligencePanel.tsx`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyCard.tsx`

- [ ] Step 1: 在 CSS 中集中加入颜色、纸纹、硬阴影、不规则圆角的 token 化变量  
- [ ] Step 2: 只给首屏主纸页、公司卡、签署区加纸张风格，岗位条目先不重拟物  
- [ ] Step 3: 验证移动端布局是否仍可读  
- [ ] Step 4: 跑构建  
Run: `cd F:\赏金猎人\.worktrees\bounty-pool-v1\frontend; npm run build`

- [ ] Step 5: Commit  
`git commit -m "feat: apply dossier paper visual system"`

---

## Phase 3：公司档案卡重构

### Task 5: 把公司卡重排成“公司档案卡”

**Files:**
- Create: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyClaimSeal.tsx`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyCard.tsx`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyCard.test.tsx`

- [ ] Step 1: 写测试，约束公司卡顶部必须包含公司名、岗位数、签署区、预计赏金  
- [ ] Step 2: 跑测试确认失败  
- [ ] Step 3: 抽出 `CompanyClaimSeal.tsx`，承接未认领 / 已认领双态  
- [ ] Step 4: 重排 `CompanyCard.tsx`，让岗位区只保留 2-3 个重点岗位摘要  
- [ ] Step 5: 跑组件测试和 build  
Run: `cd F:\赏金猎人\.worktrees\bounty-pool-v1\frontend; npm test && npm run build`

- [ ] Step 6: Commit  
`git commit -m "feat: redesign company cards as claimable dossiers"`

### Task 6: 接入预计赏金展示

**Files:**
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\home_feed_aggregation.py`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyClaimSeal.tsx`
- Test: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_home_feed_aggregation.py`

- [ ] Step 1: 先补后端测试，表达“有估算值时显示金额，无估算值时显示待估算”  
- [ ] Step 2: 跑测试确认失败  
- [ ] Step 3: 后端先实现占位和最小估算输出（无须复杂算法）  
- [ ] Step 4: 前端签署区稳定渲染该字段  
- [ ] Step 5: 跑后端测试和前端构建  

- [ ] Step 6: Commit  
`git commit -m "feat: add estimated bounty to company dossiers"`

---

## Phase 4：单公司线索来信

### Task 7: 定义单公司线索来信契约

**Files:**
- Create: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\schemas\company_clue.py`
- Create: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\company_clue_letter.py`
- Test: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_company_clue_letter.py`

- [ ] Step 1: 写失败测试，表达输出必须至少有：
  - `status`
  - `narrative`
  - `sections`
  - `company`
  - `generated_at`

- [ ] Step 2: 跑测试确认失败  
- [ ] Step 3: 实现最小 schema 和 service 骨架，只允许接收系统已有信息  
- [ ] Step 4: 跑测试通过  
- [ ] Step 5: Commit  
`git commit -m "feat: add company clue letter contract"`

### Task 8: 接入 LLM 生成链路，并写死输入边界

**Files:**
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\company_clue_letter.py`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\app\services\intelligence.py`（只复用已有 LLM 客户端或共用 helper）
- Test: `F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_company_clue_letter.py`

- [ ] Step 1: 只允许喂给模型系统已有字段：
  - 公司名 / 官网 / 招聘页 / 原帖 / 邮箱
  - 重点岗位
  - 标签
  - v2 reasons / rule_hits
  - 时间压力 / 异常 / 关键性
  - 预计赏金

- [ ] Step 2: 禁止项写入 prompt：
  - 不额外联网搜索
  - 不猜联系人
  - 不伪造 fallback 来信

- [ ] Step 3: 跑服务层测试，确保失败时直接返回失败状态  
- [ ] Step 4: Commit  
`git commit -m "feat: implement llm company clue letters"`

### Task 9: 接入公司卡按钮与便笺式弹层

**Files:**
- Create: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyClueTrigger.tsx`
- Create: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyClueLetter.tsx`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyCard.tsx`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\lib\api.ts`
- Modify: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\lib\types.ts`
- Test: `F:\赏金猎人\.worktrees\bounty-pool-v1\frontend\components\CompanyCard.test.tsx`

- [ ] Step 1: 写失败测试，约束公司卡出现 `侦查线索` 按钮和 loading 三段轮播  
- [ ] Step 2: 跑测试确认失败  
- [ ] Step 3: 实现按钮、loading、便笺弹层  
- [ ] Step 4: 来信结构按三块固定：
  - `我先看到的`
  - `这说明什么`
  - `你下一步怎么动`

- [ ] Step 5: 跑前端测试与 build  
Run: `cd F:\赏金猎人\.worktrees\bounty-pool-v1\frontend; npm test && npm run build`

- [ ] Step 6: Commit  
`git commit -m "feat: add company clue letter interaction"`

---

## Phase 5：收口与验收

### Task 10: 端到端回归

**Files:**
- Test only

- [ ] Step 1: 跑后端关键测试  
Run: `pytest F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_home_api.py F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_home_feed_aggregation.py F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_claim_service.py F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_intelligence.py F:\赏金猎人\.worktrees\bounty-pool-v1\backend\tests\test_company_clue_letter.py -q`

- [ ] Step 2: 跑前端构建  
Run: `cd F:\赏金猎人\.worktrees\bounty-pool-v1\frontend; npm run build`

- [ ] Step 3: 手工验收关键路径  
检查：
  - 首页首屏是否为情报封面
  - 公司卡是否已切为公司级认领语义
  - 预计赏金是否稳定
  - `侦查线索` 是否能生成来信
  - 失败时是否直接提示失败

- [ ] Step 4: Commit  
`git commit -m "test: verify redesigned dossier flow"`

---

## 依赖顺序说明

必须按这个顺序做：

1. 先收公司级契约和认领语义  
2. 再重排首页信息架构  
3. 再重构公司档案卡  
4. 再补预计赏金  
5. 最后接单公司线索来信

原因：

- 公司级语义不先稳定，后面的 UI 都会返工
- 首页结构不先定，视觉系统会失焦
- 公司卡不先重构，`侦查线索` 没有合适的落点
- 预计赏金和签署区是公司卡的主交互锚点，必须先于单公司来信落稳

## 本阶段明确不做

- 完整 BD 线索数据库
- 额外联网搜索 / 联系人深爬
- 数据库迁移
- 缓存单公司线索来信
- 复杂协作权限与认领转移
- 切换首页主 API 契约

## 风险提醒

1. 公司级认领会牵动当前 claim 语义，必须先稳住后端聚合和前端主语。
2. 预计赏金缺少足够薪资数据时，第一版要接受大量 `待估算`。
3. 单公司线索来信是高期待动作，LLM 质量和失败提示必须明确，不要伪装 fallback。
4. 纸张风格必须只强化首屏、公司卡和便笺，不能把整页做成花哨手帐。

