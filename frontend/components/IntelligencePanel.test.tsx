import React from "react";
import { render, screen } from "@testing-library/react";

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
    expect(screen.getByText(intelligence.headline)).toBeInTheDocument();
    expect(screen.getByText(intelligence.summary)).toBeInTheDocument();
  });

  it("renders the right-side notes content without requiring expand", () => {
    const intelligence = buildIntelligence();

    render(
      <IntelligencePanel intelligence={intelligence} previewBucket="today" previewCompanies={[buildCompany()]} />,
    );

    expect(screen.getByText(/侧栏注记|注记区/)).toBeInTheDocument();
    expect(screen.getByText(intelligence.findings[0])).toBeInTheDocument();
    expect(screen.getByText(intelligence.findings[1])).toBeInTheDocument();
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
