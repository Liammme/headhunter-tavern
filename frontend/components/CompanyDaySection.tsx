import React from "react";

import CompanyCard from "./CompanyCard";
import type { CompanyCardPayload, DayBucketPayload } from "../lib/types";

export default function CompanyDaySection({
  bucket,
  companies,
  showTitle = true,
  defaultVisibleJobs,
  showJobExpand,
  showTrustRail = true,
  showClueAction = true,
}: {
  bucket: DayBucketPayload["bucket"];
  companies: CompanyCardPayload[];
  showTitle?: boolean;
  defaultVisibleJobs?: number;
  showJobExpand?: boolean;
  showTrustRail?: boolean;
  showClueAction?: boolean;
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
            showTrustRail={showTrustRail}
            showClueAction={showClueAction}
          />
        ))}
      </div>
    </section>
  );
}

function renderBucketTitle(bucket: DayBucketPayload["bucket"]) {
  if (bucket === "within_3_days") {
    return "3天内";
  }
  if (bucket === "within_7_days") {
    return "7天内";
  }
  return "更早";
}
