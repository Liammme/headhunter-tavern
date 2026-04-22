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
  it("renders as a company dossier card while preserving actionable company and job details", () => {
    render(
      <CompanyCard
        company={buildCompany({
          company_url: "https://companies.example.com/opengradient",
          claimed_names: ["Ada"],
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
    expect(within(card as HTMLElement).getByText("Ada")).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Principal AI Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).getByRole("heading", { level: 4, name: "Growth Engineer" })).toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("公司线索认领：")).toBeInTheDocument();
    expect(within(card as HTMLElement).getAllByText("岗位认领：").length).toBeGreaterThan(0);
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
