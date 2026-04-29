# 赏金池假招聘与 Scam 风险层设计

日期：2026-04-29

## 1. 背景

赏金池当前已经能抓取岗位、按公司聚合、做 v2 机会评分、展示公司档案卡、支持公司级认领，并且可以按公司生成 LLM 线索来信。

用户提出的关键风险是：如果抓取到的岗位本身是假招聘、钓鱼岗位、过期岗位、虚假薪资或 scam，产品不能把这些岗位包装成“机会”，否则会消耗猎头时间、损害候选人信任，甚至带来安全风险。

这个问题不能靠一句“平台不负责”解决。产品需要承担的责任是：在不承诺岗位真实的前提下，尽早暴露风险信号，避免把高风险岗位积极推荐给用户。

## 2. 核心结论

第一版不要做“真假岗位判定器”，而要做“招聘风险初筛层”。

产品表达上，不能说：

- `平台认证岗位`
- `真实可靠`
- `官方推荐`
- `已审核无风险`
- `放心推荐`
- `保障成交`
- `高可信岗位`

更稳妥的表达是：

- `未发现明显风险`
- `需核验`
- `疑似风险`
- `高风险`
- `请核验公司主体与申请入口`
- `平台仅展示已识别风险信号，不保证岗位真实`

工程上，风险层必须和现有机会评分层解耦：

- `score-v2` 继续回答“这个岗位有没有 BD / 猎头机会”。
- `scam-risk-v1` 单独回答“这个岗位或公司有没有假招聘 / scam 风险信号”。
- 首页、公司卡、情报、线索来信只消费风险结果，不在各自模块里重复写规则。
- LLM 只解释已有风险信号，不负责做第一判断源。

## 3. 四类视角收敛

### 3.1 资深产品用户视角

资深猎头用户真正担心的不是系统能否证明岗位真实，而是：

- 浪费 BD 时间。
- 把候选人推给不靠谱岗位。
- 被钓鱼链接、私聊入口、付费要求误导。
- 平台看起来像是在替这些岗位背书。

因此产品需要优先展示：

- 公司主体是否清楚。
- 公司链接和岗位链接是否可信。
- 是否存在付款、押金、私钥、下载 App、短链、私人联系方式等高危信号。
- 岗位是否长期重复、描述空泛、薪资异常。
- 风险信号来自哪里，为什么被标出来。

第一版不应该做复杂雇主信用体系，也不应该承诺“已验证真实”。

### 3.2 长期招聘行业 HR 视角

招聘行业里的风险不只是一种 scam，而是多种混合形态：

- `假招聘`：岗位不真实开放，只是收简历、做人才库、刷活跃。
- `钓鱼岗位`：诱导候选人点击外链、下载 App、填写敏感信息、付款。
- `过期岗位`：HC 已关闭但页面未下架。
- `虚假薪资`：薪资展示夸张，实际面试后压薪或拆成复杂绩效。
- `外包/中介伪装`：包装成甲方直招，实际是外包、派遣、RPO 或供应商。
- `岗位描述不实`：标题是核心岗位，实际是销售、拉新、培训贷、低端执行。
- `公司主体异常`：招聘公司、用工公司、发薪公司、合同主体不一致。
- `灰产/高风险业务`：博彩、刷单、资金盘、违规拉新、违规催收等。
- `试岗/作品套取`：要求无偿完成可商用方案、代码、设计或运营策略。

系统不能保证：

- HC 仍然开放。
- 薪资最终兑现。
- 岗位一定直签。
- 公司真实用工体验。
- 单条 JD 足以判定诈骗。

所以第一版应输出风险标签和核验建议，而不是输出绝对结论。

### 3.3 产品经理视角

这不是一个“黑名单产品”，而是“公司可信度与招聘真实性风险雷达”。

产品主路径应是：

- 用户先看到公司机会。
- 同时看到风险等级和关键风险原因。
- 点击线索时，LLM 不能无视风险继续鼓励 BD。
- 认领前如有中高风险，应提示用户先核验。

产品上必须把“机会价值”和“风险可信度”拆开展示：

- `高价值 / 低风险`
- `高价值 / 需核验`
- `中价值 / 高风险`

不要把高风险岗位直接变成低赏金岗位，因为那会掩盖真正原因。一个岗位可以很有机会，但仍然很危险。

### 3.4 产品研发视角

风险识别应作为独立 service 放在 `job_enrichment` 之后、首页聚合和 LLM 之前。

推荐链路：

```text
crawlers
  -> job_enrichment
    -> job_facts
    -> score-v2
    -> scam_risk
  -> job_upsert / payload
  -> home_feed_aggregation
  -> intelligence / company_clue_letter
  -> frontend display
```

这样做的原因：

- crawler 只负责采集，不做业务判断。
- job_facts 只提供事实，不输出 scam 结论。
- score-v2 不混入风险判断。
- aggregation / intelligence / company_clue_letter 只消费风险结果，不重复规则。
- 后续如果风险层要持久化，可以独立演进。

## 4. 第一版目标

第一版目标不是“识别所有假招聘”，而是做到以下四件事：

1. 明显 scam 信号可被识别和解释。
2. 中高风险岗位不会被 LLM 积极推荐为 BD 机会。
3. 用户在认领公司前能看到风险提示。
4. 产品不再给用户“平台已经验证岗位真实”的错觉。

完成标准：

- 每条风险判断都有可解释 `rule_hit`。
- 首页公司卡能显示公司级风险摘要。
- 公司线索来信会读取风险上下文。
- 高风险岗位不会进入积极推荐话术。
- 单元测试覆盖高危规则、阈值、首页聚合和 LLM 输入边界。

## 5. 第一版不做什么

第一版明确不做：

- 不承诺岗位真实。
- 不承诺公司安全。
- 不做完整第三方尽调。
- 不做法律担保或赔付。
- 不做复杂 ML 模型。
- 不让 LLM 作为第一判断源。
- 不做公开黑名单。
- 不自动封禁所有中高风险岗位。
- 不自动访问可疑外链做深度验证。
- 不把风险分混入 `score-v2`。
- 不为了安全把所有可疑岗位直接隐藏。

## 6. 风险等级

第一版使用四档：

```text
low      未发现明显风险
medium   需核验
high     疑似高风险
blocked  高风险拦截
```

建议阈值：

```text
0-24: low
25-49: medium
50-79: high
80-100 或命中强拦截规则: blocked
```

展示文案建议：

- `low`：`未发现明显风险`
- `medium`：`需核验`
- `high`：`疑似高风险`
- `blocked`：`高风险拦截`

不要展示成：

- `真实`
- `安全`
- `已验证`
- `平台认证`

## 7. 风险分类

第一版建议覆盖以下风险分类：

### 7.1 公司主体风险

典型信号：

- 公司名为空、Unknown、个人名、明显假名或测试名。
- 公司链接缺失。
- 公司域名和岗位申请链接域名不一致。
- 招聘主体、官网主体、合同主体疑似不一致。
- 公司成立时间短但大量发布高薪岗位。
- 公司业务和岗位内容明显不匹配。

第一版可先用已有字段做弱判断，不引入第三方工商查询。

### 7.2 联系方式风险

典型信号：

- 引导添加私人微信、Telegram、WhatsApp、QQ。
- 使用个人邮箱或免费邮箱冒充公司直招。
- 邮箱域名和公司域名不一致。
- 使用短链、网盘、陌生表单、App 下载页。
- 要求扫码进群但无法验证主体。

注意：Web3 岗位可能合法出现 Telegram / Discord / wallet 等词，不能只因关键词出现就直接判 `blocked`。必须结合公司信息缺失、付款要求、私聊导流等上下文。

### 7.3 付费与敏感信息风险

典型高危信号：

- 要求押金、培训费、体检费、工装费、认证费。
- 要求充值、质押资产、购买课程。
- 要求银行卡、验证码、身份证正反面、紧急联系人。
- 要求私钥、助记词、钱包签名、交易截图。

这类信号应进入 `blocked` 或至少 `high`。

### 7.4 薪资与收益异常

典型信号：

- “无经验高薪”“日结高薪”“轻松月入”“稳赚”。
- 薪资远高于同岗位常识，但 JD 极短。
- “综合薪资”不拆底薪、绩效、提成、补贴。
- 岗位看似技术或产品，描述实际是拉新、销售、地推。

第一版不需要做行业薪资库，只做文本和结构异常识别。

### 7.5 JD 质量风险

典型信号：

- JD 少于合理长度。
- 缺少职责、技能、业务场景。
- 只有福利、愿景、口号。
- 标题和职责不匹配。
- 大量模板化营销词。

### 7.6 来源完整性风险

典型信号：

- 岗位链接失效或明显跳转异常。
- source_name 缺失。
- canonical_url 重复异常。
- 同公司同标题长期重复发布。
- collected_at 很新但 posted_at 很旧。

## 8. 规则引擎设计

新增独立模块建议命名：

```text
backend/app/services/scam_risk.py
```

该模块只做纯函数风险判断，不依赖 ORM、DB、API、前端组件。

### 8.1 输入 DTO

建议结构：

```python
@dataclass(frozen=True)
class ScamRiskInput:
    canonical_url: str
    source_name: str
    title: str
    company: str
    company_url: str | None
    description: str
    posted_at: datetime | None
    collected_at: datetime
    facts: JobFacts
    raw_payload: dict[str, Any]
```

输入边界原则：

- 可以读取标准化岗位字段。
- 可以读取 `JobFacts`。
- 可以读取 `raw_payload` 中已有的公司链接、申请链接、邮箱等结构化字段。
- 不主动抓外部网页。
- 不调用 LLM。

### 8.2 输出 DTO

建议结构：

```python
@dataclass(frozen=True)
class ScamRiskRuleHit:
    code: str
    dimension: str
    severity: str
    weight: int
    evidence: str


@dataclass(frozen=True)
class ScamRiskResult:
    risk_score: int
    risk_level: str
    rule_version: str
    should_downrank: bool
    should_exclude_from_positive_llm: bool
    should_require_review: bool
    reasons: tuple[str, ...]
    rule_hits: tuple[ScamRiskRuleHit, ...]
```

字段说明：

- `risk_score`：仅用于内部排序和阈值，不在第一版主界面突出显示。
- `risk_level`：前端主展示字段。
- `rule_version`：例如 `scam-risk-v1`。
- `should_downrank`：首页排序可用。
- `should_exclude_from_positive_llm`：LLM 不能把它当积极机会。
- `should_require_review`：后续人工复核队列可用。
- `reasons`：给用户看的短理由。
- `rule_hits`：给测试、调试、后续人工审核看的证据。

### 8.3 写入位置

第一版不做数据库迁移时，可以把轻量结果写入 `signal_tags`：

```python
"scam_risk": {
    "risk_score": 65,
    "risk_level": "high",
    "rule_version": "scam-risk-v1",
    "should_downrank": true,
    "should_exclude_from_positive_llm": true,
    "should_require_review": true,
    "reasons": [
        "申请入口疑似绕过官方渠道",
        "岗位描述信息不足且薪资表达异常"
    ],
    "rule_hits": [
        {
            "code": "contact.off_platform_private_chat",
            "dimension": "contact",
            "severity": "high",
            "weight": 30
        }
    ]
}
```

后续如果要做风险历史、人工复核、误报反馈，再单独引入持久化表。

## 9. 第一版规则建议

### 9.1 强拦截规则

命中以下任一类，建议直接进入 `blocked`：

- 要求候选人付款、押金、培训费、认证费、充值。
- 要求提供私钥、助记词、钱包签名、交易截图。
- 要求验证码、银行卡、身份证正反面等敏感信息。
- 明确引导到陌生 App 下载页并要求注册或充值。

这些不是普通“招聘真实性”问题，而是候选人安全风险。

### 9.2 高风险规则

建议加权：

- 私人微信 / Telegram / WhatsApp 导流，且公司主体信息缺失：`+30`
- 短链、网盘、陌生表单作为申请入口：`+25`
- 公司名为空或 Unknown，且 JD 出现快速赚钱类话术：`+35`
- 薪资异常高，且 JD 缺少职责和技能要求：`+25`
- 岗位标题和描述严重不匹配：`+20`

### 9.3 中风险规则

建议加权：

- JD 少于 80 字：`+15`
- 缺少 company_url：`+5`
- 缺少 posted_at：`+5`
- 邮箱域名和公司域名不一致：`+15`
- “急招、名额有限、当天入职、不看学历、无需经验、包过”等营销词密集：`+20`
- 同公司同标题频繁重复：`+15`

### 9.4 低风险规则

建议加权：

- 只有岗位链接，没有公司链接：`+5`
- 来源字段不完整：`+5`
- 时间信息不完整：`+5`

低风险规则不能单独造成高风险，只能作为辅助信号。

## 10. 首页与公司卡展示

公司卡应显示公司级风险摘要，而不是每个岗位都铺满风险文案。

建议展示位置：

- 公司名区域附近显示一个小标签。
- 线索按钮旁或公司档案元信息区显示风险等级。
- 展开岗位证据时，具体岗位可以显示命中的风险标签。

展示示例：

```text
需核验
原因：申请入口疑似非官方渠道；岗位描述信息不足
```

高风险示例：

```text
疑似高风险
先核验公司主体与申请入口，再决定是否认领
```

认领前交互：

- `low`：正常认领。
- `medium`：认领区显示轻量提醒。
- `high`：认领前显示明确提醒，但第一版不强制禁止。
- `blocked`：不建议出现在普通首页公司卡；如出现，应禁用认领并提示人工复核。

## 11. 对排序和评分的影响

风险层不改写 `bounty_grade`。

可以在聚合层使用独立惩罚：

```text
effective_rank_score = opportunity_rank_score - risk_penalty
```

建议惩罚：

```text
low: 0
medium: -10
high: -35
blocked: exclude from normal feed
```

这样保留了两个事实：

- 一个岗位可以机会很高。
- 同一个岗位也可能风险很高。

用户需要同时看到这两个维度。

## 12. 对 LLM 情报和线索来信的影响

LLM 不能判断“真假”，只能解释系统已经识别出的风险信号。

### 12.1 LLM 输入

可以给 LLM：

```json
{
  "risk_level": "high",
  "risk_reasons": ["申请入口疑似非官方渠道", "岗位描述信息不足"],
  "safe_action": "verify_company_before_contact"
}
```

不要给 LLM：

- 微信号
- Telegram 号
- WhatsApp 号
- 钱包地址
- 私钥 / 助记词相关内容
- 短链
- 疑似付款入口

### 12.2 首页情报 prompt 约束

首页情报应增加硬规则：

- 不得把 `high` 或 `blocked` 岗位写成积极机会。
- 不得写“放心联系”“已验证真实”。
- 如果市场机会集中在中高风险公司，应明确说“机会和风险并存，需要先核验”。
- 如有 blocked 样本，只能作为风险趋势统计，不进入推荐样本。

### 12.3 公司线索来信 prompt 约束

公司线索来信应增加硬规则：

- 如果公司风险为 `high`，James 侦探可以解释风险，但不能建议直接 BD。
- 如果公司风险为 `blocked`，返回安全提醒，不生成 BD 话术。
- 如果公司风险为 `medium`，输出核验清单优先于行动建议。
- 如果公司风险为 `low`，也只能说“未发现明显风险”，不能说“真实可靠”。

## 13. 人工核验与反馈

第一版可以先不做完整后台，但设计上应预留以下动作：

- `标记误报`
- `确认风险`
- `忽略本次风险`
- `加入人工复核`
- `举报岗位`

这些动作不应直接写进评分层。后续应独立成 `risk_review` 或 `moderation` 边界。

猎头触达前的建议核验流程：

1. 核验岗位来源、发布时间、最近更新时间。
2. 核验公司主体、官网、岗位链接是否一致。
3. 核验 HC 是否真实开放。
4. 核验薪资结构，包括底薪、绩效、提成、补贴和试用期。
5. 核验用工性质，是直签、外包、派遣、RPO 还是猎头代招。
6. 核验流程安全性，是否要求付款、下载 App、提交敏感资料。
7. 记录核验状态，避免重复踩坑。

## 14. 技术落地顺序

### Phase 1：风险规则契约

目标：只建立风险层 DTO、纯函数规则和单测。

建议改动：

- 新增 `backend/app/services/scam_risk.py`
- 新增 `backend/tests/test_scam_risk.py`

验证：

```powershell
cd F:\赏金猎人\.worktrees\bounty-pool-v1\backend
pytest tests/test_scam_risk.py -q
```

### Phase 2：接入 enrichment

目标：在写路径中生成 `signal_tags["scam_risk"]`，但不改首页展示。

建议改动：

- `backend/app/services/job_enrichment.py`
- `backend/tests/test_job_enrichment.py`

验证：

```powershell
pytest tests/test_scam_risk.py tests/test_job_enrichment.py -q
```

### Phase 3：首页聚合消费

目标：公司级聚合风险摘要，blocked 不进入普通积极推荐样本。

建议改动：

- `backend/app/services/home_feed_aggregation.py`
- `backend/app/services/feed_snapshot.py`
- `backend/app/schemas/home.py`
- `backend/tests/test_home_feed_aggregation.py`
- `backend/tests/test_home_api.py`

验证：

```powershell
pytest tests/test_home_feed_aggregation.py tests/test_home_api.py -q
```

### Phase 4：前端风险展示

目标：公司卡显示风险等级和短理由，认领前显示轻量提醒。

建议改动：

- `frontend/lib/types.ts`
- `frontend/components/CompanyCard.tsx`
- `frontend/components/CompanyClaimSeal.tsx`
- `frontend/components/CompanyCard.test.tsx`

验证：

```powershell
cd F:\赏金猎人\.worktrees\bounty-pool-v1\frontend
npm test -- components/CompanyCard.test.tsx
npm run build
```

### Phase 5：LLM 风险约束

目标：首页情报和公司线索来信读取风险上下文，不再积极推荐高风险公司。

建议改动：

- `backend/app/services/intelligence.py`
- `backend/app/services/company_clue_letter.py`
- `backend/tests/test_intelligence.py`
- `backend/tests/test_company_clue_letter.py`

验证：

```powershell
pytest tests/test_intelligence.py tests/test_company_clue_letter.py -q
```

### Phase 6：人工反馈闭环

目标：如产品验证需要，再新增举报、误报、确认风险等能力。

这一步需要单独设计，不应混进第一轮规则层。

## 15. 测试清单

后端测试应覆盖：

- 付款、押金、私钥、助记词命中 `blocked`。
- Web3 正常岗位出现 wallet / blockchain 不应被误杀。
- JD 极短只应中低风险，不能单独 blocked。
- 多个弱信号叠加能进入 `medium` 或 `high`。
- 阈值边界：24/25、49/50、79/80。
- `job_enrichment` 输出包含 `signal_tags["scam_risk"]`。
- 首页聚合能生成公司级风险摘要。
- `blocked` 不进入积极推荐样本。
- 公司线索来信在 high / blocked 情况下不生成鼓励 BD 的话术。

前端测试应覆盖：

- `low` 显示 `未发现明显风险`。
- `medium` 显示 `需核验`。
- `high` 显示明确风险提示。
- `blocked` 禁用或隐藏认领入口。
- 没有风险字段时保持兼容。

## 16. 成功指标

第一版上线后，至少观察这些信号：

- 高风险岗位是否被明显标出。
- 用户是否在认领前能看到风险提示。
- LLM 是否还会推荐高风险岗位。
- 被标风险的岗位是否有明显误伤。
- 用户是否仍然需要手动逐条判断来源可信度。
- 是否出现“平台认证真实”这类误导性表达。

## 17. 推荐决策

推荐采用以下默认策略：

- 第一版做规则引擎，不做 LLM 判定器。
- 第一版不改 `score-v2`，只新增独立 `scam-risk-v1`。
- 第一版中高风险先提示和降权，`blocked` 才退出普通 feed。
- 第一版不做数据库迁移，先把结果写入 `signal_tags["scam_risk"]`。
- 第一版不做公开黑名单和复杂人工后台。
- 第一版必须修改 LLM prompt，禁止积极推荐高风险公司。

这条路线的好处是：能快速降低产品责任风险，同时不会把现有评分、首页、线索来信和抓取链路搅在一起。
