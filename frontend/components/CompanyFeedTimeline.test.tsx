import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import CompanyFeedTimeline from "./CompanyFeedTimeline";
import type { DayBucketPayload } from "../lib/types";

vi.mock("./CompanyCard", () => ({
  default: ({ company }: { company: { company: string } }) => <article>{company.company}</article>,
}));

function buildDay(bucket: DayBucketPayload["bucket"], company: string): DayBucketPayload {
  return {
    bucket,
    companies: [
      {
        company,
        company_grade: "focus",
        total_jobs: 1,
        claimed_names: [],
        jobs: [],
      },
    ],
  };
}

describe("CompanyFeedTimeline", () => {
  it("shows today and yesterday by default, and expands earlier buckets on demand", () => {
    render(
      <CompanyFeedTimeline
        days={[buildDay("today", "Today Co"), buildDay("yesterday", "Yesterday Co"), buildDay("earlier", "Earlier Co")]}
      />,
    );

    expect(screen.getByRole("heading", { level: 2, name: "今天" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "昨天" })).toBeInTheDocument();
    expect(screen.queryByText("Earlier Co")).not.toBeInTheDocument();

    const toggle = screen.getByRole("button", { name: "展开更早岗位" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    fireEvent.click(toggle);

    expect(screen.getByText("Earlier Co")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "收起更早岗位" })).toHaveAttribute("aria-expanded", "true");
  });
});
