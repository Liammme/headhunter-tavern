import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import CompanyFeedTimeline from "./CompanyFeedTimeline";
import type { DayBucketPayload } from "../lib/types";

vi.mock("./CompanyCard", () => ({
  default: ({ company }: { company: { company: string; jobs: Array<{ title: string }> } }) => (
    <article>
      <h3>{company.company}</h3>
      {company.jobs.map((job) => (
        <p key={job.title}>{job.title}</p>
      ))}
    </article>
  ),
}));

function buildDay(bucket: DayBucketPayload["bucket"], company: string, jobCount = 1): DayBucketPayload {
  return {
    bucket,
    companies: [
      {
        company,
        company_grade: "focus",
        total_jobs: jobCount,
        claimed_names: [],
        jobs: Array.from({ length: jobCount }, (_, index) => ({
          id: index + 1,
          title: `${company} Job ${index + 1}`,
          canonical_url: `https://jobs.example.com/${company}-${index + 1}`,
          bounty_grade: "medium",
          tags: [],
          claimed_names: [],
        })),
      },
    ],
  };
}

describe("CompanyFeedTimeline", () => {
  it("switches between today, yesterday, and earlier with horizontal tabs", () => {
    render(
      <CompanyFeedTimeline
        days={[buildDay("today", "Today Co"), buildDay("yesterday", "Yesterday Co"), buildDay("earlier", "Earlier Co")]}
      />,
    );

    expect(screen.getByRole("tab", { name: "今天" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Today Co")).toBeInTheDocument();
    expect(screen.queryByText("Yesterday Co")).not.toBeInTheDocument();
    expect(screen.queryByText("Earlier Co")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "昨天" }));

    expect(screen.getByText("Yesterday Co")).toBeInTheDocument();
    expect(screen.queryByText("Today Co")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "更早" }));

    expect(screen.getByText("Earlier Co")).toBeInTheDocument();
  });

  it("limits the earlier tab to ten jobs until expanded", () => {
    render(<CompanyFeedTimeline days={[buildDay("earlier", "Earlier Co", 12)]} />);

    fireEvent.click(screen.getByRole("tab", { name: "更早" }));

    expect(screen.getByText("Earlier Co Job 10")).toBeInTheDocument();
    expect(screen.queryByText("Earlier Co Job 11")).not.toBeInTheDocument();

    const toggle = screen.getByRole("button", { name: "展开全部更早岗位" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(toggle);

    expect(screen.getByText("Earlier Co Job 12")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "收起更早岗位" })).toHaveAttribute("aria-expanded", "true");
  });
});
