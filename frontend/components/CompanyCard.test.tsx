import React from "react";
import { render, screen, within } from "@testing-library/react";

import CompanyCard from "./CompanyCard";
import type { CompanyCardPayload } from "../lib/types";

vi.mock("./ClaimDialog", () => ({
  default: () => <button type="button">认领</button>,
}));

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
    expect(within(card as HTMLElement).getByText("重点公司")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("共 2 个岗位")).toBeInTheDocument();
    const seal = within(card as HTMLElement).getByLabelText("公司签署状态位");
    expect(within(card as HTMLElement).getByRole("button", { name: "线索" })).toBeInTheDocument();
    expect(within(seal).getByText("Signed by Ada")).toBeInTheDocument();
    expect(within(seal).getByText("待估算")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Principal AI Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Growth Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("重点岗位证据")).toBeInTheDocument();
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
});
