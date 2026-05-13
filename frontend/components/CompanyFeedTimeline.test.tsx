import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import CompanyFeedTimeline from "./CompanyFeedTimeline";
import type { DayBucketPayload, JobCategory } from "../lib/types";

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

function buildDay(
  bucket: DayBucketPayload["bucket"],
  company: string,
  jobCategories: JobCategory[] = ["技术"],
): DayBucketPayload {
  return {
    bucket,
    companies: [
      {
        company,
        company_grade: "focus",
        total_jobs: jobCategories.length,
        claimed_names: [],
        jobs: jobCategories.map((jobCategory, index) => ({
          id: index + 1,
          title: `${company} Job ${index + 1}`,
          canonical_url: `https://jobs.example.com/${company}-${index + 1}`,
          bounty_grade: "medium",
          job_category: jobCategory,
          tags: [],
          claimed_names: [],
        })),
      },
    ],
  };
}

describe("CompanyFeedTimeline", () => {
  it("switches between recent buckets with horizontal tabs", () => {
    render(
      <CompanyFeedTimeline
        days={[
          buildDay("within_3_days", "Recent Co"),
          buildDay("within_7_days", "Week Co"),
          buildDay("earlier", "Earlier Co"),
        ]}
      />,
    );

    expect(screen.getByRole("tab", { name: "最新" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Recent Co")).toBeInTheDocument();
    expect(screen.queryByText("Week Co")).not.toBeInTheDocument();
    expect(screen.queryByText("Earlier Co")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "7天内" }));

    expect(screen.getByText("Week Co")).toBeInTheDocument();
    expect(screen.queryByText("Recent Co")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "更早" }));

    expect(screen.getByText("Earlier Co")).toBeInTheDocument();
  });

  it("limits the earlier tab to ten jobs until expanded", () => {
    render(
      <CompanyFeedTimeline
        days={[
          buildDay("earlier", "Earlier Co", Array.from({ length: 12 }, (): JobCategory => "技术")),
        ]}
      />,
    );

    fireEvent.click(screen.getByRole("tab", { name: "更早" }));

    expect(screen.getByText("Earlier Co Job 10")).toBeInTheDocument();
    expect(screen.queryByText("Earlier Co Job 11")).not.toBeInTheDocument();

    const toggle = screen.getByRole("button", { name: "展开全部更早岗位" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(toggle);

    expect(screen.getByText("Earlier Co Job 12")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "收起更早岗位" })).toHaveAttribute("aria-expanded", "true");
  });

  it("filters visible jobs by backend job category", () => {
    render(
      <CompanyFeedTimeline
        days={[
          {
            bucket: "within_3_days",
            companies: [
              buildDay("within_3_days", "Design Co", ["设计"]).companies[0],
              buildDay("within_3_days", "Data Co", ["数据"]).companies[0],
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText("Design Co")).toBeInTheDocument();
    expect(screen.getByText("Data Co")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "岗位类型 全部" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "设计" }));

    expect(screen.getByText("Design Co")).toBeInTheDocument();
    expect(screen.queryByText("Data Co")).not.toBeInTheDocument();
  });

  it("shows an empty state when the selected category has no jobs", () => {
    render(<CompanyFeedTimeline days={[buildDay("within_3_days", "Tech Co", ["技术"])]} />);

    fireEvent.click(screen.getByRole("button", { name: "岗位类型 全部" }));
    fireEvent.click(screen.getByRole("checkbox", { name: "设计" }));

    expect(screen.getByText("这一栏暂时没有匹配岗位")).toBeInTheDocument();
    expect(screen.queryByText("Tech Co")).not.toBeInTheDocument();
  });

  it("keeps category options hidden until the filter button opens them", () => {
    render(<CompanyFeedTimeline days={[buildDay("within_3_days", "Design Co", ["设计"])]} />);

    expect(screen.queryByRole("checkbox", { name: "设计" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "岗位类型 全部" }));

    expect(screen.getByRole("checkbox", { name: "设计" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "岗位类型 全部" })).toHaveAttribute("aria-expanded", "true");
  });
});
