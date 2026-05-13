import React from "react";
import { fireEvent, render, screen, within } from "@testing-library/react";

import IntelligencePanel from "./IntelligencePanel";
import type { IntelligencePayload } from "../lib/types";

function buildIntelligence(overrides: Partial<IntelligencePayload> = {}): IntelligencePayload {
  return {
    headline: "新增 12 家公司进入观察池，算法与增长岗位开始抬头",
    summary: "今天先盯住新增密集的公司卡片，再顺手筛掉重复 JD。",
    narrative: "近 14 天里，算法工程与增长岗位开始同步回升，适合优先看有连续发布动作的公司。",
    findings: ["右侧注记：新增公司集中在 AI 工具与企业服务。", "右侧注记：重复岗位主要出现在同组招聘团队。"],
    actions: ["榜单引导：先看今日新增最多的公司。", "露头信号：连续两天都在发相近岗位的团队值得先跟。"],
    living_report: null,
    ...overrides,
  };
}

function buildLivingReport(): NonNullable<IntelligencePayload["living_report"]> {
  return {
    kind: "living_market_report",
    schema_version: "living-market-report-v1",
    headline: "AI infra 保持结构性可见",
    version: 2,
    mode: "incremental_update",
    previous_snapshot_id: 1,
    seed_window_days: 180,
    generated_at: "2026-04-27T10:00:00",
    executive_summary: "AI infra 在长期样本中保持可见，短期变化仍需观察。",
    sections: [
      {
        section_id: "market_structure",
        title: "市场结构",
        body: "AI infra 是当前样本中最稳定的结构性主题。",
        claim_ids: ["c1"],
      },
      {
        section_id: "demand_shifts",
        title: "需求变化",
        body: "短窗信号没有脱离 180 天基线。",
        claim_ids: ["c2"],
      },
    ],
    claims: [
      {
        claim_id: "c1",
        previous_claim_id: "c0",
        status: "reinforced",
        claim: "AI infra 保持可见。",
        confidence: "medium",
        evidence_ids: ["e1"],
        evidence_notes: ["AI infra 在 180d 和 30d 窗口都可见。"],
        change_reason: "新增事实继续支持上一版判断。",
      },
      {
        claim_id: "c2",
        previous_claim_id: null,
        status: "new",
        claim: "短期变化不足以证明全面升温。",
        confidence: "low",
        evidence_ids: ["e1"],
        evidence_notes: ["7d 样本仍较小。"],
        change_reason: "新增保守判断。",
      },
    ],
    watchlist: [
      {
        topic: "AI infra",
        why_watch: "观察 30 天窗口是否继续扩大。",
        evidence_ids: ["e1"],
      },
    ],
    data_quality: {
      baseline_note: "当前可见岗位的历史基线，不代表完整真实半年历史。",
      posted_at_fact_count: 8,
      collected_at_fallback_count: 0,
      unknown_company_count: 0,
      sample_count: 8,
    },
  };
}

describe("IntelligencePanel", () => {
  const captureTitle = "近3天岗位 5 个 / 点击切换市场报告";
  const collectionStats = [
    { label: "3天内", value: 5 },
    { label: "7天内", value: 3 },
    { label: "更早", value: 12 },
  ];

  it("shows the collection chart by default and reveals intelligence on demand", () => {
    const intelligence = buildIntelligence();
    const reportDateLabel = "2026/4/23";

    const { container } = render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel={reportDateLabel}
        captureTitle={captureTitle}
        captureDescription="分布来源：OpenGradient、Beta Labs。"
        collectionStats={collectionStats}
      />,
    );

    expect(screen.getByRole("heading", { level: 3, name: captureTitle })).toBeInTheDocument();
    expect(screen.getByText("分布来源：OpenGradient、Beta Labs。")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "每日岗位收集数量统计图" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "3天内，5 个岗位" }).length).toBeGreaterThan(0);
    expect(screen.getByText("Daily Capture Signal")).toBeInTheDocument();
    const chartVisual = container.querySelector(".animated-chart-visual");
    expect(chartVisual).not.toHaveClass("is-active");
    fireEvent.mouseEnter(chartVisual as Element);
    expect(chartVisual).toHaveClass("is-active");
    expect(screen.queryByRole("heading", { level: 2, name: intelligence.headline })).not.toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "查看猎场控制台" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "返回" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("region", { name: "打开猎场控制台" }));

    expect(screen.getByRole("heading", { level: 2, name: intelligence.headline })).toBeInTheDocument();
    const paper = screen.getByRole("article", { name: reportDateLabel });
    expect(screen.getByRole("button", { name: "返回" })).toBeInTheDocument();
    expect(within(paper).getByRole("heading", { level: 3, name: reportDateLabel })).toBeInTheDocument();
    expect(within(paper).getByText(intelligence.narrative)).toBeInTheDocument();
    expect(within(paper).queryByText("分布来源：OpenGradient、Beta Labs。")).not.toBeInTheDocument();
    expect(within(paper).queryByText(intelligence.summary)).not.toBeInTheDocument();
    expect(container.querySelector(".intel-footnote")).not.toBeInTheDocument();
    expect(screen.queryByText(intelligence.summary)).not.toBeInTheDocument();

    fireEvent.click(paper);

    expect(screen.getByRole("heading", { level: 2, name: intelligence.headline })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "返回" }));

    expect(screen.getByRole("heading", { level: 3, name: captureTitle })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: intelligence.headline })).not.toBeInTheDocument();
  });

  it("reveals the living report after clicking the chart", () => {
    const intelligence = buildIntelligence({ living_report: buildLivingReport() });

    const { container } = render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/27"
        captureTitle={captureTitle}
        captureDescription="分布来源：OpenGradient。"
        collectionStats={collectionStats}
      />,
    );

    expect(screen.getByRole("heading", { level: 3, name: captureTitle })).toBeInTheDocument();
    expect(screen.queryByText("第 2 版")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("region", { name: "打开猎场控制台" }));

    expect(screen.getByText("第 2 版")).toBeInTheDocument();
    expect(screen.getByText("基于 180 天基线")).toBeInTheDocument();
    expect(screen.getByText("最近更新 2026-04-27T10:00:00")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "AI infra 保持结构性可见" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "市场结构" })).toBeInTheDocument();
    expect(screen.getByText("AI infra 保持可见。")).toBeInTheDocument();
    expect(screen.getByText("观察 30 天窗口是否继续扩大。")).toBeInTheDocument();
    expect(screen.getByText("样本数 8")).toBeInTheDocument();
    expect(container.querySelector(".living-report-scroll")).toBeInTheDocument();
  });

  it("falls back to the legacy narrative when living_report is absent", () => {
    const intelligence = buildIntelligence({ living_report: null });

    render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/27"
        captureTitle={captureTitle}
        captureDescription="分布来源：OpenGradient。"
        collectionStats={collectionStats}
      />,
    );

    fireEvent.click(screen.getByRole("region", { name: "打开猎场控制台" }));

    expect(screen.getByText(intelligence.narrative)).toBeInTheDocument();
    expect(screen.queryByText("基于 180 天基线")).not.toBeInTheDocument();
  });

  it("renders an empty sections fallback for malformed living report content", () => {
    const livingReport = buildLivingReport();
    livingReport.sections = [];
    const intelligence = buildIntelligence({ living_report: livingReport });

    render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/27"
        captureTitle={captureTitle}
        captureDescription="分布来源：OpenGradient。"
        collectionStats={collectionStats}
      />,
    );

    fireEvent.click(screen.getByRole("region", { name: "打开猎场控制台" }));

    expect(screen.getByText("暂无可展示章节。")).toBeInTheDocument();
  });

  it("opens the living report with Enter and Space", () => {
    const intelligence = buildIntelligence({ living_report: buildLivingReport() });

    const { rerender } = render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/27"
        captureTitle={captureTitle}
        captureDescription="分布来源：OpenGradient。"
        collectionStats={collectionStats}
      />,
    );

    fireEvent.keyDown(screen.getByRole("region", { name: "打开猎场控制台" }), { key: "Enter" });
    expect(screen.getByText("第 2 版")).toBeInTheDocument();

    rerender(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/27"
        captureTitle={captureTitle}
        captureDescription="分布来源：OpenGradient。"
        collectionStats={collectionStats}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "返回" }));
    fireEvent.keyDown(screen.getByRole("region", { name: "打开猎场控制台" }), { key: " " });
    expect(screen.getByText("第 2 版")).toBeInTheDocument();
  });

  it("uses recent bucket labels when collection stats are empty", () => {
    render(
      <IntelligencePanel
        intelligence={buildIntelligence()}
        reportDateLabel="2026/4/23"
        captureTitle="近3天岗位 0 个"
        captureDescription="分布来源：暂无公司来源。"
        collectionStats={[]}
      />,
    );

    expect(screen.getAllByRole("button", { name: "3天内，0 个岗位" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "7天内，0 个岗位" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "更早，0 个岗位" }).length).toBeGreaterThan(0);
  });

  it("breaks a multi-sentence narrative into letter-like paragraphs", () => {
    const intelligence = buildIntelligence({
      narrative:
        "James侦探晃了晃杯底，低声说：今天先盯核心产研岗。和近14天摊开的盘子比，今天真正冒头的不是热闹标签。你示意他继续，他把话说透：优先抢技术、AI、产品里的高赏金核心岗。",
    });

    const { container } = render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/24"
        captureTitle="近3天岗位 12 个"
        captureDescription="分布来源：Aijobs。"
        collectionStats={collectionStats}
      />,
    );

    fireEvent.click(screen.getByRole("region", { name: "打开猎场控制台" }));

    const narrativeParagraphs = container.querySelectorAll(".intel-narrative");

    expect(narrativeParagraphs).toHaveLength(3);
    expect(narrativeParagraphs[0]).toHaveTextContent("James侦探晃了晃杯底");
    expect(narrativeParagraphs[1]).toHaveTextContent("今天真正冒头的不是热闹标签");
    expect(narrativeParagraphs[2]).toHaveTextContent("优先抢技术、AI、产品里的高赏金核心岗");
  });

  it("renders every paragraph from a long intelligence narrative inside the paper copy", () => {
    const longNarrativeSections = [
      "第一段：James先把今天新增岗位按公司聚在一起，提醒你不要被单个高薪标题带偏。",
      "第二段：AI 工具链公司在过去 14 天里连续露头，但真正值得先看的，是同一团队反复补算法和后端的位置。",
      "第三段：企业服务方向的增长岗位开始回暖，尤其是同时出现销售运营、数据分析和产品经理的公司。",
      "第四段：重复 JD 不是噪音，它可能说明招聘团队在多个渠道试水，也可能说明岗位描述还没被业务方校准。",
      "第五段：今天的行动顺序应该先看连续发布动作，再看赏金金额，最后才回头补齐公司背景。",
      "第六段：如果你只能处理三家公司，优先选择新岗位多、岗位族稳定、且最近两天都在更新的团队。",
    ];
    const intelligence = buildIntelligence({
      narrative: longNarrativeSections.join("\n\n"),
    });

    const { container } = render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/25"
        captureTitle="近3天岗位 18 个"
        captureDescription="分布来源：Aijobs、RemoteHub。"
        collectionStats={collectionStats}
      />,
    );

    fireEvent.click(screen.getByRole("region", { name: "打开猎场控制台" }));

    const paperCopy = container.querySelector(".intel-paper-copy");

    expect(paperCopy).toBeInTheDocument();
    longNarrativeSections.forEach((section) => {
      expect(within(paperCopy as HTMLElement).getByText(section)).toBeInTheDocument();
    });
  });

  it("does not render the secondary intelligence note cards", () => {
    const intelligence = buildIntelligence();

    render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/23"
        captureTitle="近3天岗位 3 个"
        captureDescription="分布来源：OpenGradient。"
        collectionStats={collectionStats}
      />,
    );

    expect(screen.queryByRole("complementary", { name: "今日行动信号" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 4, name: "情报发现" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 4, name: "跟进动作" })).not.toBeInTheDocument();
    expect(screen.queryByText(intelligence.findings[0])).not.toBeInTheDocument();
    expect(screen.queryByText(intelligence.findings[1])).not.toBeInTheDocument();
    expect(screen.queryByText(intelligence.actions[0])).not.toBeInTheDocument();
    expect(screen.queryByText(intelligence.actions[1])).not.toBeInTheDocument();
  });

  it("does not render ranking guidance or the removed peek block", () => {
    const intelligence = buildIntelligence();

    render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/23"
        captureTitle="近3天岗位 3 个"
        captureDescription="分布来源：OpenGradient。"
        collectionStats={collectionStats}
      />,
    );

    expect(screen.queryByText(/榜单引导|露头信号/)).not.toBeInTheDocument();
    expect(screen.queryByText(intelligence.actions[0])).not.toBeInTheDocument();
    expect(screen.queryByText(intelligence.actions[1])).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 3, name: "今日机会雷达" })).not.toBeInTheDocument();
    expect(screen.queryByText("榜单露头")).not.toBeInTheDocument();
    expect(screen.queryByText("找找看有没有能BD的公司？")).not.toBeInTheDocument();
  });
});
