import React from "react";

import CompanyCard from "./CompanyCard";
import type { CompanyCardPayload, DayBucketPayload } from "../lib/types";

export default function CompanyDaySection({
  bucket,
  companies,
  showTitle = true,
  defaultVisibleJobs,
  showJobExpand,
}: {
  bucket: DayBucketPayload["bucket"];
  companies: CompanyCardPayload[];
  showTitle?: boolean;
  defaultVisibleJobs?: number;
  showJobExpand?: boolean;
}) {
  return (
    <section className="day-section">
      {showTitle ? <h2 className="day-title">{renderBucketTitle(bucket)}</h2> : null}
      <div className="company-list">
        {companies.map((company) => (
          <CompanyCard
            key={`${bucket}-${company.company}`}
            company={company}
            defaultVisibleJobs={defaultVisibleJobs}
            showJobExpand={showJobExpand}
          />
        ))}
      </div>
    </section>
  );
}

function renderBucketTitle(bucket: DayBucketPayload["bucket"]) {
  if (bucket === "today") {
    return "今天";
  }
  if (bucket === "yesterday") {
    return "昨天";
  }
  return "更早";
}
