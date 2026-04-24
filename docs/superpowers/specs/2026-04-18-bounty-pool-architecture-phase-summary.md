# 赏金池架构收口阶段总结

## 1. 本阶段目标

本阶段的目标不是继续大拆，而是在不破坏现有产品可用性的前提下，把主链路收口到一个可以进入人工 review 和产品验收的状态。

核心目标包括：

1. 让 `claims`、`home`、`crawl` 三条主链 API 具备明确 service 边界
2. 让首页查询链具备清晰的聚合、情报、组装边界
3. 让 `crawl_pipeline.py` 从“大总管”收口为更薄的 orchestrator
4. 让 `scoring.py` 保持纯函数特征
5. 让首页与 `猎场情报` 共享同一分析基线
6. 在不做重型 schema 迁移的前提下，为读模型补齐 `analysis_version` / `rule_version` 这类过渡元信息
7. 补齐关键主链测试，确保阶段性结构可验证、可回滚

---

## 2. 本阶段完成的关键架构调整

### 2.1 API 层收口

`claims`、`home`、`crawl` 三个 API 入口均已从直接承载业务逻辑，收口为“请求入口 + service 调用”模式。

当前边界为：

1. `api/claims.py -> claim_service`
2. `api/home.py -> home_query_service`
3. `api/crawl.py -> crawl_trigger_service`

这让 API 层不再直接承担认领创建、首页查询组织、抓取触发编排。

### 2.2 首页查询链拆分

首页查询链已经从单一 `home_feed.py` 的混合实现，推进为以下结构：

1. `home_query_service` 负责首页查询入口
2. `home_feed` 负责读路径编排
3. `home_feed_aggregation` 负责聚合 / 排序
4. `intelligence` 负责情报快照生成
5. `home_feed_assembler` 负责首页 payload 组装

首页不再在组装层重新做聚合判断，情报也不再独立走另一套静态逻辑。

### 2.3 抓取写路径拆分

抓取写路径已经从单文件聚合，拆成更清晰的链路：

1. `crawl_trigger_service` 负责触发入口
2. `crawl_pipeline` 负责 orchestrator
3. `crawl_fetch_service` 负责抓取执行与错误汇总
4. `job_enrichment` 负责岗位富化 / 事实提取类纯函数
5. `job_upsert_service` 负责去重、入库、过期清理

当前 `crawl_pipeline.py` 已不再直接持有抓取执行、岗位富化、入库细节三类职责。

### 2.4 评分层收口

`scoring.py` 已引入结构化输入输出：

1. `JobScoreInput`
2. `JobScoreResult`
3. `RULE_VERSION`

当前评分层仍保持纯函数模式，没有引入数据库、API、crawler adapter 或前端文案依赖。

### 2.5 统一分析基线

首页和 `猎场情报` 现在共享同一批聚合结果和同一套元信息：

1. `day_payloads`
2. `FeedMetadata`
3. `analysis_version`
4. `rule_version`
5. `window_start`
6. `window_end`
7. `generated_at`

这意味着情报不再是独立占位文案，而是建立在首页同一聚合基线之上。

### 2.6 读模型过渡结构

本阶段没有做数据库级别的新表迁移，但已经引入轻量读模型过渡结构：

1. `JobFeedSnapshot`
2. `CompanyFeedSnapshot`
3. `DayBucketSnapshot`
4. `FeedMetadata`

这为“原始事实 / 派生分析 / 展示快照”三分边界提供了服务层过渡实现。

---

## 3. 已完成的提交列表及其作用

### 3.1 第一轮职责拆分

1. `a04f546` `refactor: extract claim creation into claim service`  
   把认领创建从 API 层下沉到独立 service。

2. `0763a0f` `refactor: split home feed aggregation from assembly`  
   把首页聚合/排序与首页组装拆开。

3. `690235d` `refactor: extract crawl job enrichment helpers`  
   把抓取链中的岗位富化、事实提取类纯函数抽出。

4. `9ef084c` `refactor: structure scoring inputs and outputs`  
   让评分层具备更明确的纯函数输入输出结构。

### 3.2 第二轮统一基线与应用服务收口

5. `1eec856` `refactor: build intelligence from feed aggregation`  
   让情报层改为消费首页聚合结果，而不是静态占位。

6. `bc9ad51` `refactor: route crawl trigger through service`  
   让抓取触发 API 改为通过独立 service 调用。

7. `e10170d` `refactor: extract crawl job upsert service`  
   把抓取写路径中的去重、入库、清理职责从 orchestrator 中抽出。

8. `13bb6e8` `refactor: introduce feed snapshot read models`  
   引入首页读模型过渡 DTO，明确聚合结果与展示快照边界。

### 3.3 技术债与最终收口

9. `f617e0a` `chore: replace model utcnow defaults`  
   清理已跟踪模型文件中的 `utcnow()` 默认值警告。

10. `d49e2b9` `chore: switch app startup to lifespan`  
    用 `lifespan` 替代 `on_event` 启动钩子。

11. `4d9dcea` `refactor: route home query through service`  
    让首页查询 API 改为通过独立查询 service 调用。

12. `f9ee5b8` `refactor: add analysis metadata to home feed`  
    为首页读模型和情报补齐版本元信息，增强统一分析基线的可追踪性。

13. `8dad1e5` `refactor: extract crawl fetch service`  
    把抓取执行和抓取结果汇总从 `crawl_pipeline.py` 中抽出。

---

## 4. 当前系统分层现状

当前系统已形成如下主链路：

1. `API 层`
   - `api/claims.py`
   - `api/home.py`
   - `api/crawl.py`

2. `应用服务 / 编排层`
   - `claim_service`
   - `home_query_service`
   - `crawl_trigger_service`
   - `home_feed`
   - `crawl_pipeline`

3. `抓取与写路径服务`
   - `crawl_fetch_service`
   - `job_enrichment`
   - `job_upsert_service`

4. `评分层`
   - `scoring`

5. `聚合 / 排序层`
   - `home_feed_aggregation`

6. `情报层`
   - `intelligence`

7. `首页组装层`
   - `home_feed_assembler`

8. `读模型过渡层`
   - `feed_snapshot`

当前分层还不是最终目录形态，但主链职责已经基本按文档要求拆开。

---

## 5. 当前已经解决的耦合点

本阶段已经明确解决的高风险耦合点包括：

1. `claims` 不再在 API handler 中直接落库创建
2. `home` 不再由 API 层直接组织首页数据
3. 首页聚合 / 排序与首页组装已拆开
4. `intelligence` 不再是静态占位文案，也不再脱离首页单独算一套基线
5. `crawl` 触发不再由 API 直接调用大总管式逻辑
6. `crawl_pipeline.py` 不再同时承担抓取执行、岗位富化、入库清理全部职责
7. `scoring.py` 没有继续长成依赖 DB / API / crawler 的混合模块
8. 首页读路径已经有统一的 `FeedMetadata` 过渡元信息，首页和情报的版本边界可追踪

---

## 6. 当前有意识不做的内容

这些内容是本阶段明确选择不做，而不是遗漏：

1. 不新增数据库表
2. 不做不可逆 schema 迁移
3. 不把 `Job` 彻底拆成事实表 + analysis snapshot + feed snapshot 三类持久化模型
4. 不做历史数据 backfill
5. 不做评分规则灰度对比
6. 不做目录级别的大重构，例如一次性迁到 `application/`、`domain/`、`infrastructure/`
7. 不碰未跟踪的 crawler adapter 源码
8. 不为了“更完美”而移除当前仍承担兼容职责的过渡 service

这些内容更适合放到下一阶段，而不是在本阶段收尾时继续扩张 review 范围。

---

## 7. 明确属于下一阶段的工作

下一阶段更适合处理的工作包括：

1. 正式把“原始事实 / 派生分析 / 展示快照”落到持久化模型
2. 引入 `JobFactSnapshot` / `JobAnalysisSnapshot` 或等价结构
3. 让 `CompanyDailySummary` / `IntelligenceSnapshot` 成为正式读模型来源
4. 支持分析结果回放与重算
5. 做评分规则版本对比与人工校验
6. 做 backfill 和灰度切换
7. 在隔离 review 范围后，单独清理未跟踪 crawler adapter 文件里的 `datetime.utcnow()` 警告

这些工作都属于“下一阶段建设”，不应伪装成“本阶段收尾”。

---

## 8. 当前风险与剩余技术债

### 8.1 当前风险

当前没有发现必须立即处理的高优先级结构风险，但仍有以下中低优先级问题：

1. `Job` 仍同时承载事实字段与部分派生分析字段
2. 首页读路径仍然是“查询时聚合 + 组装”，尚未切到正式持久化快照
3. 情报虽然已共享首页基线，但还没有形成真正落库的 snapshot 产物

### 8.2 剩余技术债

1. 未跟踪 crawler adapter 文件中仍有 `datetime.utcnow()` 弃用警告
2. 当前工作区仍存在与本阶段无关的未提交项，例如 `backend/pyproject.toml`
3. 目录结构仍是过渡态，尚未演进到长期推荐结构

这些问题都真实存在，但不构成本阶段必须继续改代码的理由。

---

## 9. 为什么建议在当前状态收尾

建议在当前状态收尾，原因如下：

1. 本阶段的核心目标已经实现  
   API 薄层、service 边界、首页与情报统一基线、抓取 orchestrator 收口、评分纯函数化，这些关键目标都已落地。

2. 当前继续重构的边际收益已经明显下降  
   再往下做，基本都会进入数据库层、历史数据、正式读模型等下一阶段工作。

3. 当前主链已经具备可验证性  
   现有关键主链测试已经覆盖 claims、crawl、home、aggregation、assembler、intelligence、enrichment、upsert、scoring。

4. 当前状态更适合进入人工 review / 产品验收  
   这时继续拆分，风险会开始超过收益，也更容易把下一阶段工作误卷入当前 review 范围。

一句话总结：

**这一阶段已经把主链从“混写闭环”推进到了“边界清晰、测试可证、可进入验收”的状态，继续改动不再是收尾，而会开始进入下一阶段建设。**
