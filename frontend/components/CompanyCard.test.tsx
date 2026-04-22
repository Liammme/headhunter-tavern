import React from "react";
import { render, screen } from "@testing-library/react";

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
