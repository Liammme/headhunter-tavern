# 前端设计系统重构设计

日期：2026-04-24  
项目：`F:\赏金猎人`  
范围：整个前端视觉系统、首页、公司卡、情报面板、认领弹窗、线索面板、响应式规则  
不含：后端业务逻辑、数据库结构、评分规则、认领规则、大模型输入输出

## 1. 背景

当前前端已经完成过一轮“侦探酒馆 / 手写档案”视觉方向，主要样式集中在 `frontend/app/globals.css`，核心页面由 `frontend/app/page.tsx` 和 `frontend/components/*` 组成。

本轮重构选择“组件系统化”路线：不是继续堆单页特殊样式，也不是只做局部美化，而是把视觉语言、基础控件、卡片、弹窗、列表和响应式规则统一成一套可长期维护的产品前端系统。

用户后续会从 21st.dev 提供 2-3 个视觉参考。实现时不直接复制某一个参考，而是提取共同组件语言，并结合“赏金猎人 / 公司猎单池 / 情报判断”的产品语义落地。

## 2. 目标

本轮重构完成后，前端应达到以下结果：

1. 页面第一眼具有明确品牌记忆点，而不是普通后台模板。
2. 全局样式有稳定 token，后续新增页面不需要继续堆孤立 CSS。
3. 首页、情报面板、公司卡、认领弹窗、线索面板属于同一套视觉系统。
4. 公司仍是榜单主语，岗位仍是证据，不把产品退回岗位列表。
5. 认领状态仍是公司级归属表达，而不是普通按钮状态。
6. 页面保持工作台效率：可扫读、可判断、可点击、移动端不崩。

## 3. 设计原则

### 3.1 系统优先

优先建立可复用的视觉规则，而不是为每个组件写独立效果。

核心样式先保留在 `frontend/app/globals.css` 中，避免第一轮就引入 CSS framework 或大规模组件库。只有当样式继续膨胀、重复明显时，才新增 `components/ui/*` 基础组件。

### 3.2 品牌强，但不牺牲效率

视觉可以强品牌化，但页面本质是工作台，不是纯 landing page。

首页首屏应有品牌气质，但必须让用户快速进入“今天看什么公司、为什么看、谁已认领”的工作流。

### 3.3 公司是第一主语

公司卡的视觉层级固定：

1. 公司名是第一锚点。
2. 认领状态是第二锚点。
3. 预计赏金稳定可见。
4. 岗位只作为证据。
5. 次要动作收敛，不抢主线。

### 3.4 小步可审查

实施时按层推进：

1. token 和基础壳层
2. 首页信息架构
3. 公司卡系统
4. 交互控件统一
5. 响应式收口
6. 测试与构建验证

每一步都应保持 diff 可读，不做无关重构。

## 4. 全局样式设计

核心文件：

- `frontend/app/globals.css`

全局 token 分四层。

### 4.1 Color

定义以下语义变量：

- 页面背景
- 主文字
- 弱文本
- 边框
- 品牌主色
- 强调色
- 成功 / 警告 / 错误
- surface 分层
- hover / active / disabled 状态

不再让所有区域共享同一种“手绘纸张”质感。纸感、纹理、强装饰只用于高价值模块，普通列表和控件要更克制。

### 4.2 Type

建立四类文字规则：

- 标题：品牌、模块标题、公司名
- 正文：情报正文、说明文字
- 数字：岗位数、赏金、统计值
- 注记：标签、来源、时间、辅助说明

字体可继续使用当前本地字体，但实现时要根据 21st.dev 参考判断是否需要收敛手写感。原则是：品牌标题可以有个性，工作信息必须可读。

### 4.3 Space

建立稳定间距：

- 页面左右 gutter
- section 间距
- 卡片内边距
- 列表 gap
- 控件间距
- 移动端压缩规则

目标是减少组件之间的“凭感觉间距”，让页面密度可控。

### 4.4 Effect

统一以下效果：

- 圆角
- 边框
- 阴影
- hover
- active
- focus-visible
- disabled
- reduced-motion

交互动效只保留两类：

- 操作反馈：按压、位移、阴影变化
- 层级反馈：hover 抬起、展开区域出现

不做持续性装饰动画。

## 5. Surface 分层

全局系统分成五类 surface：

### 5.1 App Shell

负责页面背景、最大宽度、响应式 gutter、主内容纵向节奏。

### 5.2 Surface

普通信息面板，用于列表分组、说明块、常规内容。

### 5.3 Feature Surface

首屏情报、重点公司档案等高价值模块使用。可以有更强品牌细节。

### 5.4 Action Surface

可点击、可认领、可展开的区域。必须有明确 hover、focus 和 disabled 状态。

### 5.5 Status Surface

空态、加载、错误、成功反馈。样式应统一，不能每个组件各写一套。

## 6. 组件边界

### 6.1 `CompanyFeedTimeline.tsx`

职责：

- 管理时间分组顺序。
- 管理“查看更多”的列表节奏。
- 不关心公司卡内部视觉细节。

不应承担：

- 公司卡布局。
- 认领状态展示。
- 岗位证据展示。

### 6.2 `CompanyDaySection.tsx`

职责：

- 展示某一天的标题。
- 承载该日公司列表。
- 可承载轻量统计摘要。

不应承担：

- 公司卡内部结构。
- 展开岗位逻辑。

### 6.3 `CompanyCard.tsx`

职责：

- 公司档案主体结构。
- 公司头部。
- 认领区插槽。
- 岗位证据区。
- 展开更多。
- 线索入口。

视觉要求：

- 公司名最大。
- 认领区稳定占位。
- 岗位区轻量，不能像第二套卡片系统。

### 6.4 `CompanyClaimSeal.tsx`

职责：

- 展示未认领 / 已认领状态。
- 提供公司级认领入口。
- 稳定显示预计赏金。

该组件应成为独立的“归属状态”组件，而不是公司卡内部随手写的按钮区。

### 6.5 `ClaimDialog.tsx`

职责：

- 弹窗结构。
- 表单输入。
- 提交 / 取消状态。

不应承担：

- 公司卡布局。
- 认领区展示。

### 6.6 `IntelligencePanel.tsx`

职责：

- 首页主情报。
- 关键数字。
- 今日方向。
- 预览公司。

如果文件体量继续增大，可拆成子组件，但第一轮不为拆而拆。

### 6.7 `CompanyCluePanel.tsx`

职责：

- 展开后的深度线索信息。
- 加载、失败、重试状态。
- 线索正文和分节展示。

视觉上应从公司卡系统派生，不能自成另一套复杂风格。

### 6.8 可选 `components/ui/*`

只有在第一轮实施中发现重复明显时，才新增：

- `components/ui/Button.tsx`
- `components/ui/Badge.tsx`
- `components/ui/Surface.tsx`

第一轮默认先用 CSS class 完成统一，避免过度抽象。

## 7. 页面改造顺序

### 7.1 建立 token 和基础壳层

修改文件：

- `frontend/app/globals.css`
- 必要时 `frontend/app/layout.tsx`

工作内容：

- 重写全局变量。
- 统一 body 背景。
- 统一页面宽度和 gutter。
- 统一按钮、输入、链接、focus、disabled 基础规则。

完成标准：

- 页面整体风格统一。
- 组件结构暂时不大动。
- 不破坏现有交互。

### 7.2 重构首页信息架构

修改文件：

- `frontend/app/page.tsx`
- `frontend/components/IntelligencePanel.tsx`

工作内容：

- 首页首屏从装饰英雄区变成产品工作台入口。
- 保留品牌识别。
- 让榜单入口在首屏底部可感知。

完成标准：

- 用户第一眼知道这是“赏金猎人”的产品。
- 用户能快速理解今天该看什么。
- 页面不是纯封面页。

### 7.3 重构公司卡系统

修改文件：

- `frontend/components/CompanyFeedTimeline.tsx`
- `frontend/components/CompanyDaySection.tsx`
- `frontend/components/CompanyCard.tsx`
- `frontend/components/CompanyClaimSeal.tsx`

工作内容：

- 统一公司卡结构。
- 强化公司名和认领状态。
- 收敛岗位证据区。
- 统一展开更多交互。

完成标准：

- 公司名是第一视觉锚点。
- 认领状态是第二视觉锚点。
- 岗位区清楚但不抢主语。
- 展开更多不造成布局混乱。

### 7.4 统一交互控件

修改文件：

- `frontend/app/globals.css`
- `frontend/components/ClaimDialog.tsx`
- `frontend/components/CompanyCluePanel.tsx`
- 其他使用按钮、标签、输入的组件

工作内容：

- 统一按钮。
- 统一标签。
- 统一输入框。
- 统一弹窗。
- 统一加载、错误、空态。

完成标准：

- 所有可点击元素属于同一套系统。
- hover / focus / disabled 行为一致。
- 弹窗和面板不再像独立页面。

### 7.5 响应式收口

检查宽度：

- 320px
- 768px
- 1024px
- 1440px

完成标准：

- 文本不溢出。
- 按钮不挤压。
- 公司卡层级不乱。
- 认领区移动端位置明确。
- 首屏不遮挡榜单入口。

### 7.6 测试与构建

先跑最小行为测试：

```powershell
cd F:\赏金猎人\frontend
npm test
```

再跑构建：

```powershell
cd F:\赏金猎人\frontend
npm run build
```

如果测试需要调整，只改和 UI 结构、可访问名称、交互状态相关的测试，不改业务断言。

## 8. 验证方式

### 8.1 自动验证

- `npm test`
- `npm run build`

### 8.2 人工视觉检查

检查场景：

- 首页默认态
- 首页空态
- 公司卡未认领
- 公司卡已认领
- 公司卡展开岗位
- 认领弹窗
- 线索面板加载中
- 线索面板成功态
- 线索面板失败态

### 8.3 响应式检查

检查宽度：

- 320px
- 768px
- 1024px
- 1440px

重点看：

- 公司名长文本
- 岗位标题长文本
- 按钮换行
- 弹窗宽度
- 认领区占位
- 情报正文行宽

## 9. 建议改动文件

第一轮大概率涉及：

- `frontend/app/globals.css`
- `frontend/app/layout.tsx`
- `frontend/app/page.tsx`
- `frontend/components/IntelligencePanel.tsx`
- `frontend/components/CompanyFeedTimeline.tsx`
- `frontend/components/CompanyDaySection.tsx`
- `frontend/components/CompanyCard.tsx`
- `frontend/components/CompanyClaimSeal.tsx`
- `frontend/components/ClaimDialog.tsx`
- `frontend/components/CompanyCluePanel.tsx`

是否新增 `frontend/components/ui/*`，由实施中的重复程度决定。

## 10. 不做项

本轮不做：

- 后端 API 改造。
- 数据库迁移。
- 评分规则升级。
- 公司认领业务规则调整。
- 大模型输入输出重构。
- 复杂权限系统。
- 新增分析、埋点、遥测或额外网络调用。
- 引入大型 UI 框架。

## 11. 成功标准

实现完成后，应满足：

1. 前端有统一 token 和基础组件语言。
2. 视觉明显强于普通后台模板。
3. 首页保留品牌记忆点，同时仍是工作台入口。
4. 公司卡层级清楚，认领区稳定，岗位区轻量。
5. 弹窗、按钮、标签、输入、状态反馈统一。
6. 移动端可用，不出现明显遮挡、溢出、错位。
7. `npm test` 和 `npm run build` 通过，或明确说明失败原因和剩余风险。
