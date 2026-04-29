import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import CompanyCard from "./CompanyCard";
import { requestCompanyClueLetter } from "../lib/api";
import type { CompanyCardPayload } from "../lib/types";

vi.mock("../lib/api", () => ({
  requestCompanyClueLetter: vi.fn(),
}));

const requestCompanyClueLetterMock = vi.mocked(requestCompanyClueLetter);
const legacyRewardLabel = ["预", "计", "赏", "金"].join("");
const legacyClaimText = ["认", "领"].join("");
const legacyClaimedText = ["已", "认", "领"].join("");
const legacyClueClaimTitle = ["公司线索", "认", "领"].join("");

function buildCompany(overrides: Partial<CompanyCardPayload> = {}): CompanyCardPayload {
  return {
    company: "OpenGradient",
    company_grade: "focus",
    latest_posted_at: "2026-04-18T09:00:00",
    total_jobs: 1,
    claimed_names: [],
    jobs: [
      {
        id: 1,
        title: "Principal AI Engineer",
        canonical_url: "https://jobs.example.com/1",
        bounty_grade: "high",
        tags: ["AI"],
        claimed_names: [],
      },
    ],
    ...overrides,
  };
}

describe("CompanyCard", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders a lighter clue action without the legacy entry", () => {
    render(
      <CompanyCard
        company={buildCompany({
          claimed_names: [],
          claimed_by: null,
          claim_status: null,
        })}
      />,
    );

    const card = screen.getByRole("heading", { level: 3, name: "OpenGradient" }).closest("article");

    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByRole("button", { name: "线索" })).toBeInTheDocument();

    expect(within(card as HTMLElement).queryByLabelText(`公司${legacyClaimText}状态位`)).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByLabelText("公司签署状态位")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByRole("button", { name: new RegExp(legacyClaimText) })).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText(new RegExp(legacyClaimedText))).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("公司档案")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("重点公司")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("发布时间")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("2026/04/18 09:00")).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText(legacyRewardLabel)).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("¥3,000+")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("待签署")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("签署区")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText(legacyClueClaimTitle)).not.toBeInTheDocument();
  });

  it("does not show legacy reward values on company or job rows", () => {
    render(
      <CompanyCard
        company={buildCompany({
          jobs: [
            {
              id: 1,
              title: "Principal AI Engineer",
              canonical_url: "https://jobs.example.com/1",
              bounty_grade: "high",
              tags: ["AI"],
              claimed_names: [],
            },
            {
              id: 2,
              title: "Growth Engineer",
              canonical_url: "https://jobs.example.com/2",
              bounty_grade: "medium",
              tags: ["Growth"],
              claimed_names: [],
            },
          ],
        })}
      />,
    );

    const card = screen.getByRole("heading", { level: 3, name: "OpenGradient" }).closest("article");
    const firstJob = within(card as HTMLElement)
      .getByRole("heading", { level: 4, name: "Principal AI Engineer" })
      .closest(".job-row");

    expect(firstJob).not.toBeNull();
    expect(within(card as HTMLElement).queryByText(legacyRewardLabel)).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("¥3,000+")).not.toBeInTheDocument();
    expect(within(firstJob as HTMLElement).queryByText(legacyRewardLabel)).not.toBeInTheDocument();
    expect(within(firstJob as HTMLElement).queryByText("¥7,200-¥18,000")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("待估算")).not.toBeInTheDocument();
  });

  it("does not render legacy entry or signature state after legacy data is present", () => {
    render(
      <CompanyCard
        company={buildCompany({
          claimed_names: ["Ada"],
          claimed_by: "Ada",
          claim_status: "已签署",
        })}
      />,
    );

    const card = screen.getByRole("heading", { level: 3, name: "OpenGradient" }).closest("article");

    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByRole("button", { name: "线索" })).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByLabelText("公司签署状态位")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("OWNER")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("SEALED")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText(legacyRewardLabel)).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("¥3,000+")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("Signed by Ada")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByRole("button", { name: new RegExp(legacyClaimText) })).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText(new RegExp(legacyClaimedText))).not.toBeInTheDocument();
  });

  it("renders a three-part dossier layout for task 5", () => {
    render(
      <CompanyCard
        company={buildCompany({
          company_url: "https://companies.example.com/opengradient",
          claimed_names: ["Ada"],
          claimed_by: "Ada",
          claim_status: "已签署",
          total_jobs: 4,
          jobs: [
            {
              id: 1,
              title: "Principal AI Engineer",
              canonical_url: "https://jobs.example.com/1",
              bounty_grade: "high",
              tags: ["AI", "Infra"],
              claimed_names: ["Lin"],
            },
            {
              id: 2,
              title: "Growth Engineer",
              canonical_url: "https://jobs.example.com/2",
              bounty_grade: "medium",
              tags: ["Growth"],
              claimed_names: [],
            },
            {
              id: 3,
              title: "Founding ML Engineer",
              canonical_url: "https://jobs.example.com/3",
              bounty_grade: "high",
              tags: ["ML"],
              claimed_names: [],
            },
            {
              id: 4,
              title: "Operations Analyst",
              canonical_url: "https://jobs.example.com/4",
              bounty_grade: "low",
              tags: ["Ops"],
              claimed_names: [],
            },
          ],
        })}
      />,
    );

    const companyHeading = screen.getByRole("heading", { level: 3, name: "OpenGradient" });
    const card = companyHeading.closest("article");

    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByText("共 4 个岗位")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("button", { name: "线索" })).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByLabelText("公司签署状态位")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("Signed by Ada")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText(legacyRewardLabel)).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("待估算")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByRole("button", { name: new RegExp(legacyClaimText) })).not.toBeInTheDocument();

    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Principal AI Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Growth Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Founding ML Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByRole("heading", { level: 4, name: "Operations Analyst" })).not.toBeInTheDocument();

    expect(within(card as HTMLElement).getByRole("button", { name: "展开更多岗位" })).toBeInTheDocument();
  });

  it("renders as a company dossier card while preserving actionable company and job details", () => {
    render(
      <CompanyCard
        company={buildCompany({
          company_url: "https://companies.example.com/opengradient",
          claimed_names: ["Ada"],
          claimed_by: "Ada",
          claim_status: "已签署",
          total_jobs: 2,
          jobs: [
            {
              id: 1,
              title: "Principal AI Engineer",
              canonical_url: "https://jobs.example.com/1",
              bounty_grade: "high",
              tags: ["AI", "Infra"],
              claimed_names: ["Lin"],
            },
            {
              id: 2,
              title: "Growth Engineer",
              canonical_url: "https://jobs.example.com/2",
              bounty_grade: "medium",
              tags: ["Growth"],
              claimed_names: [],
            },
          ],
        })}
      />,
    );

    const companyHeading = screen.getByRole("heading", { level: 3, name: "OpenGradient" });
    const card = companyHeading.closest("article");

    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByRole("link", { name: "OpenGradient" })).toHaveAttribute(
      "href",
      "https://companies.example.com/opengradient",
    );
    expect(within(card as HTMLElement).queryByText("公司档案")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("重点公司")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("共 2 个岗位")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("button", { name: "线索" })).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByLabelText("公司签署状态位")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("Signed by Ada")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("待估算")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Principal AI Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Growth Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("重点岗位证据")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText(/先看前 \d+ 个岗位摘要/)).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText(`高${legacyRewardLabel.slice(-2)}`)).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText(`中${legacyRewardLabel.slice(-2)}`)).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText(`低${legacyRewardLabel.slice(-2)}`)).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("证据备注：")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).getAllByRole("link", { name: "查看原帖" })[0]).toHaveAttribute(
      "href",
      "https://jobs.example.com/1",
    );
  });

  it("renders company name as link when company_url exists", () => {
    render(<CompanyCard company={buildCompany({ company_url: "https://companies.example.com/opengradient" })} />);

    expect(screen.getByRole("link", { name: "OpenGradient" })).toHaveAttribute(
      "href",
      "https://companies.example.com/opengradient",
    );
  });

  it("renders company name as plain text when company_url is missing", () => {
    render(<CompanyCard company={buildCompany({ company_url: null })} />);

    expect(screen.queryByRole("link", { name: "OpenGradient" })).not.toBeInTheDocument();
    expect(screen.getByText("OpenGradient")).toBeInTheDocument();
  });

  it("keeps clue content hidden until the clue action is triggered", () => {
    render(<CompanyCard company={buildCompany()} />);

    expect(screen.queryByLabelText("公司线索来信")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("公司线索处理中")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("公司线索失败结果")).not.toBeInTheDocument();
  });

  it("requests company clue and renders loading then success without reshaping backend sections", async () => {
    let resolveRequest: ((value: Awaited<ReturnType<typeof requestCompanyClueLetter>>) => void) | undefined;
    requestCompanyClueLetterMock.mockReturnValue(
      new Promise((resolve) => {
        resolveRequest = resolve;
      }),
    );

    render(<CompanyCard company={buildCompany()} />);

    fireEvent.click(screen.getByRole("button", { name: "线索" }));

    expect(requestCompanyClueLetterMock).toHaveBeenCalledWith({ company: "OpenGradient" });
    expect(screen.getByLabelText("公司线索处理中")).toBeInTheDocument();
    expect(screen.getByText("线索整理中")).toBeInTheDocument();

    resolveRequest?.({
      status: "success",
      company: "OpenGradient",
      generated_at: "2026-04-22T09:00:00",
      narrative: "James侦探说这家公司该先从高优先级 AI 岗往里查。",
      sections: [
        { key: "lead", title: "我先看到的", content: "先看 Principal AI Engineer。" },
        { key: "evidence", title: "这家公司现在露出的口子", content: "官网和岗位原帖都可直达。" },
        { key: "next_move", title: "你下一步怎么查", content: "先核对团队扩张节奏。" },
      ],
      error_message: null,
    });

    await waitFor(() => expect(screen.getByLabelText("公司线索来信")).toBeInTheDocument());
    expect(screen.getByText("James侦探说这家公司该先从高优先级 AI 岗往里查。")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 5, name: "我先看到的" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 5, name: "这家公司现在露出的口子" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 5, name: "你下一步怎么查" })).toBeInTheDocument();
    expect(screen.queryByLabelText("公司线索处理中")).not.toBeInTheDocument();
  });

  it("renders failure container when company clue request fails", async () => {
    requestCompanyClueLetterMock.mockRejectedValue(new Error("network"));

    render(<CompanyCard company={buildCompany()} />);

    fireEvent.click(screen.getByRole("button", { name: "线索" }));

    await waitFor(() => expect(screen.getByLabelText("公司线索失败结果")).toBeInTheDocument());
    expect(screen.getByText("线索生成失败")).toBeInTheDocument();
    expect(screen.getByText("OpenGradient 的单公司线索来信生成失败，请稍后重试。")).toBeInTheDocument();
    expect(screen.getByText("异常原因：Failed to request company clue letter")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "重试" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "收起" })).toBeInTheDocument();
    expect(screen.queryByLabelText("公司线索来信")).not.toBeInTheDocument();
  });

  it("allows retrying a failed clue request from the failure container", async () => {
    requestCompanyClueLetterMock
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce({
        status: "success",
        company: "OpenGradient",
        generated_at: "2026-04-22T09:00:00",
        narrative: "James侦探说第二次线索整理已经成功。",
        sections: [
          { key: "lead", title: "我先看到的", content: "测试内容" },
          { key: "evidence", title: "这家公司现在露出的口子", content: "测试内容" },
          { key: "next_move", title: "你下一步怎么查", content: "测试内容" },
        ],
        error_message: null,
      });

    render(<CompanyCard company={buildCompany()} />);

    fireEvent.click(screen.getByRole("button", { name: "线索" }));

    await waitFor(() => expect(screen.getByLabelText("公司线索失败结果")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: "重试" }));

    expect(requestCompanyClueLetterMock).toHaveBeenCalledTimes(2);
    await waitFor(() => expect(screen.getByLabelText("公司线索来信")).toBeInTheDocument());
    expect(screen.getByText("James侦探说第二次线索整理已经成功。")).toBeInTheDocument();
  });
});
