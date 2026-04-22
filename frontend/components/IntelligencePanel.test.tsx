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

    render(
      <IntelligencePanel
        intelligence={intelligence}
        previewBucket="today"
        previewCompanies={[buildCompany(), buildCompany({ company: "Beta Labs", company_grade: "watch", total_jobs: 2 })]}
      />,
    );

    expect(screen.getByText("猎场情报")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: intelligence.headline })).toBeInTheDocument();
    const paper = screen.getByRole("article", { name: "今天的判断" });
    expect(within(paper).getByText(intelligence.summary)).toBeInTheDocument();
    expect(within(paper).getByText(intelligence.narrative)).toBeInTheDocument();
  });

  it("keeps secondary intelligence grouped in sidebar sections instead of flattening all fields equally", () => {
    const intelligence = buildIntelligence();

    render(
      <IntelligencePanel intelligence={intelligence} previewBucket="today" previewCompanies={[buildCompany()]} />,
    );

    const notes = screen.getByRole("complementary", { name: "今天怎么跟" });

    expect(screen.getByText("侧栏注记")).toBeInTheDocument();
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
      <IntelligencePanel intelligence={intelligence} previewBucket="today" previewCompanies={[buildCompany()]} />,
    );

    expect(screen.getAllByText(/榜单引导|露头信号/).length).toBeGreaterThan(0);
    expect(screen.getByText(intelligence.actions[0])).toBeInTheDocument();
    expect(screen.getByText(intelligence.actions[1])).toBeInTheDocument();
    expect(screen.getByText("OpenGradient")).toBeInTheDocument();
  });
});
