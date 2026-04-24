import React from "react";
import { render, screen, within } from "@testing-library/react";

import IntelligencePanel from "./IntelligencePanel";
import type { CompanyCardPayload, IntelligencePayload } from "../lib/types";

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

function buildCompany(overrides: Partial<CompanyCardPayload> = {}): CompanyCardPayload {
  return {
    company: "OpenGradient",
    company_grade: "focus",
    total_jobs: 3,
    claimed_names: [],
    jobs: [],
    ...overrides,
  };
}

describe("IntelligencePanel", () => {
  it("renders the primary intelligence content above the fold", () => {
    const intelligence = buildIntelligence();
    const reportDateLabel = "2026/4/23";

    render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel={reportDateLabel}
        dailyCaptureSummary="今日抓取 5 个岗位，分布来源：OpenGradient、Beta Labs。"
        previewBucket="today"
        previewCompanies={[buildCompany(), buildCompany({ company: "Beta Labs", company_grade: "watch", total_jobs: 2 })]}
      />,
    );

    expect(screen.getByText("猎场情报")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: intelligence.headline })).toBeInTheDocument();
    const paper = screen.getByRole("article", { name: reportDateLabel });
    expect(within(paper).getByRole("heading", { level: 3, name: reportDateLabel })).toBeInTheDocument();
    expect(within(paper).getByText("今日抓取 5 个岗位，分布来源：OpenGradient、Beta Labs。")).toBeInTheDocument();
    expect(within(paper).queryByText(intelligence.narrative)).not.toBeInTheDocument();
    expect(within(paper).queryByText(intelligence.summary)).not.toBeInTheDocument();
    expect(screen.getByText(intelligence.summary)).toBeInTheDocument();
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
        previewBucket="today"
        previewCompanies={[buildCompany()]}
      />,
    );

    const narrativeParagraphs = container.querySelectorAll(".intel-narrative");

    expect(narrativeParagraphs).toHaveLength(3);
    expect(narrativeParagraphs[0]).toHaveTextContent("今日抓取 12 个岗位");
    expect(narrativeParagraphs[1]).toHaveTextContent("分布来源：Aijobs");
    expect(narrativeParagraphs[2]).toHaveTextContent("重点公司 2 家");
  });

  it("keeps secondary intelligence grouped in sidebar sections instead of flattening all fields equally", () => {
    const intelligence = buildIntelligence();

    render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/23"
        dailyCaptureSummary="今日抓取 3 个岗位，分布来源：OpenGradient。"
        previewBucket="today"
        previewCompanies={[buildCompany()]}
      />,
    );

    const notes = screen.getByRole("complementary", { name: "侧栏注记" });

    expect(within(notes).queryByText("今天怎么跟")).not.toBeInTheDocument();
    expect(within(notes).queryByText("把今天最值得跟的两条线索贴出来，再进入行动。")).not.toBeInTheDocument();
    expect(within(notes).getByRole("heading", { level: 4, name: "情报发现" })).toBeInTheDocument();
    expect(within(notes).getByRole("heading", { level: 4, name: "跟进动作" })).toBeInTheDocument();
    expect(within(notes).getByText(intelligence.findings[0])).toBeInTheDocument();
    expect(within(notes).getByText(intelligence.findings[1])).toBeInTheDocument();
    expect(within(notes).getByText(intelligence.actions[0])).toBeInTheDocument();
    expect(within(notes).getByText(intelligence.actions[1])).toBeInTheDocument();
    expect(within(notes).queryByText(intelligence.summary)).not.toBeInTheDocument();
    expect(within(notes).queryByText(intelligence.narrative)).not.toBeInTheDocument();
  });

  it("renders ranking guidance or early-signal cues on first paint", () => {
    const intelligence = buildIntelligence();

    render(
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel="2026/4/23"
        dailyCaptureSummary="今日抓取 3 个岗位，分布来源：OpenGradient。"
        previewBucket="today"
        previewCompanies={[buildCompany()]}
      />,
    );

    expect(screen.getAllByText(/榜单引导|露头信号/).length).toBeGreaterThan(0);
    expect(screen.getByText(intelligence.actions[0])).toBeInTheDocument();
    expect(screen.getByText(intelligence.actions[1])).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "今日招聘" })).toBeInTheDocument();
    expect(screen.getByText("找找看有没有能BD的公司？")).toBeInTheDocument();
    expect(screen.getByText("OpenGradient")).toBeInTheDocument();
  });
});
