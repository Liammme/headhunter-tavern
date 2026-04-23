import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import CompanyCard from "./CompanyCard";
import { requestCompanyClueLetter } from "../lib/api";
import type { CompanyCardPayload } from "../lib/types";

vi.mock("./ClaimDialog", () => ({
  default: () => <button type="button">认领</button>,
}));

vi.mock("../lib/api", () => ({
  requestCompanyClueLetter: vi.fn(),
}));

const requestCompanyClueLetterMock = vi.mocked(requestCompanyClueLetter);

function buildCompany(overrides: Partial<CompanyCardPayload> = {}): CompanyCardPayload {
  return {
    company: "OpenGradient",
    company_grade: "focus",
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

  it("renders a lighter clue action and a simplified unclaimed right rail for task 5.5", () => {
    render(
      <CompanyCard
        company={buildCompany({
          estimated_bounty_label: "¥3,000+",
          claimed_names: [],
          claimed_by: null,
          claim_status: null,
        })}
      />,
    );

    const card = screen.getByRole("heading", { level: 3, name: "OpenGradient" }).closest("article");

    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByRole("button", { name: "线索" })).toBeInTheDocument();

    const rightRail = within(card as HTMLElement).getByLabelText("公司认领状态位");
    expect(rightRail).not.toBeNull();
    expect(within(rightRail as HTMLElement).getByText("¥3,000+")).toBeInTheDocument();
    expect(within(rightRail as HTMLElement).getByRole("button", { name: /认领/ })).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("公司档案")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("重点公司")).toBeInTheDocument();
    expect(within(rightRail as HTMLElement).queryByText("待签署")).not.toBeInTheDocument();
    expect(within(rightRail as HTMLElement).queryByText("签署区")).not.toBeInTheDocument();
    expect(within(rightRail as HTMLElement).queryByText("公司线索认领")).not.toBeInTheDocument();
  });

  it("shows a stamped or english signature state with estimated bounty after claim for task 5.5", () => {
    render(
      <CompanyCard
        company={buildCompany({
          claimed_names: ["Ada"],
          claimed_by: "Ada",
          claim_status: "已签署",
          estimated_bounty_label: "¥3,000+",
        })}
      />,
    );

    const card = screen.getByRole("heading", { level: 3, name: "OpenGradient" }).closest("article");
    const rightRail = within(card as HTMLElement).getByLabelText("公司签署状态位");

    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByRole("button", { name: "线索" })).toBeInTheDocument();
    expect(rightRail).not.toBeNull();
    expect(within(rightRail as HTMLElement).getByText("¥3,000+")).toBeInTheDocument();
    expect(within(rightRail as HTMLElement).getByText("SEALED")).toBeInTheDocument();
    expect(within(rightRail as HTMLElement).getByText("Signed by Ada")).toBeInTheDocument();
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
    const seal = within(card as HTMLElement).getByLabelText("公司签署状态位");

    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).getByText("共 4 个岗位")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("button", { name: "线索" })).toBeInTheDocument();
    expect(within(seal).getByText("Signed by Ada")).toBeInTheDocument();
    expect(within(seal).getByText("预计赏金")).toBeInTheDocument();
    expect(within(seal).getByText("待估算")).toBeInTheDocument();
    expect(within(seal).queryByRole("button", { name: /认领/ })).not.toBeInTheDocument();

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
          estimated_bounty_label: "待估算",
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
    const seal = within(card as HTMLElement).getByLabelText("公司签署状态位");
    expect(within(card as HTMLElement).getByRole("button", { name: "线索" })).toBeInTheDocument();
    expect(within(seal).getByText("Signed by Ada")).toBeInTheDocument();
    expect(within(seal).getByText("待估算")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Principal AI Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Growth Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("重点岗位证据")).toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("高赏金")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("中赏金")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByText("低赏金")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).getAllByText("证据备注：").length).toBeGreaterThan(0);
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
      narrative: "James侦探说这家公司该先从高赏金 AI 岗往里查。",
      sections: [
        { key: "lead", title: "我先看到的", content: "先看 Principal AI Engineer。" },
        { key: "evidence", title: "这家公司现在露出的口子", content: "官网和岗位原帖都可直达。" },
        { key: "next_move", title: "你下一步怎么查", content: "先核对团队扩张节奏。" },
      ],
      error_message: null,
    });

    await waitFor(() => expect(screen.getByLabelText("公司线索来信")).toBeInTheDocument());
    expect(screen.getByText("James侦探说这家公司该先从高赏金 AI 岗往里查。")).toBeInTheDocument();
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
