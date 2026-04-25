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
    ...overrides,
  };
}

describe("IntelligencePanel", () => {
  const collectionStats = [
    { label: "今天", value: 5 },
    { label: "昨天", value: 3 },
    { label: "更早", value: 12 },
  ];

  it("shows the collection chart by default and reveals intelligence on demand", () => {
    const intelligence = buildIntelligence();
    const reportDateLabel = "2026/4/23";

    const { container } = render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel={reportDateLabel}
        dailyCaptureSummary="今日抓取 5 个岗位，分布来源：OpenGradient、Beta Labs。"
        collectionStats={collectionStats}
      />,
    );

    expect(screen.getByRole("heading", { level: 3, name: "每日岗位收集数量" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "每日岗位收集数量统计图" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "今天，5 个岗位" }).length).toBeGreaterThan(0);
    expect(screen.getByText("Daily Capture Signal")).toBeInTheDocument();
    const chartVisual = container.querySelector(".animated-chart-visual");
    expect(chartVisual).not.toHaveClass("is-active");
    fireEvent.mouseEnter(chartVisual as Element);
    expect(chartVisual).toHaveClass("is-active");
    expect(screen.queryByRole("heading", { level: 2, name: intelligence.headline })).not.toBeInTheDocument();

    expect(screen.queryByRole("button", { name: "查看猎场控制台" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("region", { name: "打开猎场控制台" }));

    expect(screen.getByRole("heading", { level: 2, name: intelligence.headline })).toBeInTheDocument();
    const paper = screen.getByRole("article", { name: reportDateLabel });
    expect(within(paper).getByRole("heading", { level: 3, name: reportDateLabel })).toBeInTheDocument();
    expect(within(paper).getByText(intelligence.narrative)).toBeInTheDocument();
    expect(within(paper).queryByText("今日抓取 5 个岗位，分布来源：OpenGradient、Beta Labs。")).not.toBeInTheDocument();
    expect(within(paper).queryByText(intelligence.summary)).not.toBeInTheDocument();
    expect(container.querySelector(".intel-footnote")).toHaveTextContent(
      "今日抓取 5 个岗位，分布来源：OpenGradient、Beta Labs。",
    );
    expect(screen.queryByText(intelligence.summary)).not.toBeInTheDocument();
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
        dailyCaptureSummary="今日抓取 12 个岗位。分布来源：Aijobs。重点公司 2 家。"
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

  it("does not render the secondary intelligence note cards", () => {
    const intelligence = buildIntelligence();

    render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/23"
        dailyCaptureSummary="今日抓取 3 个岗位，分布来源：OpenGradient。"
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
        dailyCaptureSummary="今日抓取 3 个岗位，分布来源：OpenGradient。"
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
