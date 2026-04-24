# 每日赏金池生成任务说明

## 1. 目标

本任务用于把当前已经可手动触发的抓取链路，收口成一个可按天运行、可观察结果、失败时不让首页空白的轻量日常任务。

当前目标不是引入调度平台，而是明确以下能力：

1. 每天任务如何触发
2. 任务跑完后如何看结果
3. 失败时如何定位问题
4. 本地和生产环境如何在每天早上 8 点运行

---

## 2. 当前运行链路

当前每日任务复用现有服务边界，不额外绕过已有主链：

1. `app.cli.daily_bounty`  
   运行入口，负责初始化 DB、创建会话、输出 JSON summary

2. `daily_bounty_service.run_daily_bounty_generation`  
   每日任务应用服务，负责：
   - 记录开始/结束时间
   - 调用 `crawl_trigger_service`
   - 调用 `home_query_service`
   - 汇总运行结果与今日首页摘要

3. `crawl_trigger_service -> crawl_pipeline`  
   复用现有抓取、富化、评分、入库链路

4. `home_query_service -> home_feed`  
   复用现有首页读路径，读取今日公司数和岗位数

这保证每日任务不会：

1. 直接调用 crawler adapter
2. 在任务层重算首页排序
3. 在 CLI 中堆业务逻辑

---

## 3. 输出结构

当前每日任务输出一段 JSON summary，字段如下：

1. `status`
   - `completed`
   - `completed_with_errors`
   - `failed`

2. `started_at`
3. `finished_at`
4. `fetched_jobs`
5. `new_jobs`
6. `source_stats`
7. `errors`
8. `today_company_count`
9. `today_job_count`

含义说明：

1. `fetched_jobs`  
   本次抓取总岗位数

2. `new_jobs`  
   本次新入库岗位数

3. `source_stats`  
   每个 source 抓到多少岗位

4. `errors`  
   每个 source 的失败信息，或任务级失败信息

5. `today_company_count` / `today_job_count`  
   当前首页 `today` 桶中的公司数和岗位数，用于确认首页基线是否已更新

---

## 4. 本地手动运行

在项目 `backend` 目录执行：

```bash
python -m app.cli.daily_bounty
```

示例输出：

```json
{
  "status": "completed_with_errors",
  "started_at": "2026-04-21T12:42:47",
  "finished_at": "2026-04-21T12:43:08",
  "fetched_jobs": 238,
  "new_jobs": 216,
  "source_stats": {
    "aijobsnet": 50,
    "cryptocurrencyjobs": 49
  },
  "errors": [
    "abetterweb3: cannot locate target collection view"
  ],
  "today_company_count": 1,
  "today_job_count": 23
}
```

解读原则：

1. `completed`  
   所有 source 都成功，且 summary 正常输出

2. `completed_with_errors`  
   至少一个 source 失败，但任务整体没有崩，首页仍可继续使用已有数据和本次成功结果

3. `failed`  
   抓取主链发生任务级异常；此时 summary 仍会尝试返回当前首页已有 `today` 摘要，便于判断产品是否仍保留旧内容

---

## 5. Windows 每天 8 点运行方式

如果当前运行环境是 Windows，本地建议使用“任务计划程序”。

建议配置：

1. 触发器  
   每天 `08:00`

2. 程序或脚本  
   `python`

3. 添加参数  
   `-m app.cli.daily_bounty`

4. 起始于  
   `F:\赏金猎人\.worktrees\bounty-pool-v1\backend`

5. 建议启用  
   - 无人登录也运行
   - 失败后按系统策略重试
   - 将标准输出重定向到日志文件时，保留最近运行记录

如果需要记录到文件，可改为：

```powershell
python -m app.cli.daily_bounty >> logs\daily-bounty.log 2>&1
```

前提是先准备好日志目录。

---

## 6. Linux / 服务器 cron 示例

如果后续部署到 Linux 或服务器环境，可使用 cron。

示例：

```cron
0 8 * * * cd /path/to/bounty-pool/backend && python -m app.cli.daily_bounty >> /path/to/logs/daily-bounty.log 2>&1
```

说明：

1. 这是服务器场景示例，不代表当前项目已经具备正式生产部署环境
2. 需要保证 Python 环境、依赖、数据库路径和工作目录都已正确配置

---

## 7. 成功与失败怎么看

### 7.1 成功判断

至少满足：

1. `status` 为 `completed` 或 `completed_with_errors`
2. `finished_at` 存在
3. `fetched_jobs`、`source_stats` 有值
4. `today_company_count`、`today_job_count` 可读

### 7.2 需要关注的异常信号

以下情况应视为需要排查：

1. `status=failed`
2. `errors` 持续包含同一 source
3. `fetched_jobs=0` 且并非预期空窗
4. `today_company_count=0` 且首页不符合预期

### 7.3 失败时的当前降级策略

当前实现不做“任务失败即清空首页”的行为。

在部分 source 失败或任务级异常时：

1. 已成功 source 的结果仍可入库
2. daily summary 仍会读取当前首页 `today` 摘要
3. 产品侧可继续保留旧首页，不会因为 daily task 失败而直接空白

---

## 8. 当前测试与验证

本次每日任务已补以下验证：

1. `tests/test_daily_bounty_service.py`
   - 成功汇总
   - 部分 source 失败仍返回 summary
   - 任务级失败仍返回当前首页摘要

2. 相关回归测试
   - `tests/test_crawl_api.py`
   - `tests/test_crawl_pipeline.py`
   - `tests/test_crawl_trigger_service.py`

此外，CLI 已在本地运行并得到真实 JSON 输出。

---

## 9. 当前不做项

本阶段明确不做以下内容：

1. 不引入任务调度平台
2. 不新增抓取运行历史表
3. 不做 schema 迁移
4. 不增加新的 API 契约
5. 不重写 crawler adapter
6. 不把 daily task 和首页展示结构直接绑定

---

## 10. 下一步建议

如果后续要继续演进，建议优先级如下：

1. 增加运行日志归档或外部日志采集
2. 引入轻量运行历史持久化，但需单独评估 schema 风险
3. 在明确部署环境后，再决定是否接入系统级任务调度或服务编排

当前阶段到此为止已经足够支撑：

1. 本地每天 8 点自动运行
2. 服务器场景后续平滑接入 cron
3. 手动排查 daily bounty 是否成功更新首页基线
