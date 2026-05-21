import React from "react";

import CompanyCard from "./CompanyCard";
import { DEFAULT_FEED_COPY, type CompanyCardCopy, type FeedCopy } from "../lib/copy";
import type { CompanyCardPayload, DayBucketPayload } from "../lib/types";

export default function CompanyDaySection({
  bucket,
  companies,
  showTitle = true,
  defaultVisibleJobs,
  showJobExpand,
  showTrustRail = true,
  showClueAction = true,
  copy = DEFAULT_FEED_COPY,
  companyCardCopy,
}: {
  bucket: DayBucketPayload["bucket"];
  companies: CompanyCardPayload[];
  showTitle?: boolean;
  defaultVisibleJobs?: number;
  showJobExpand?: boolean;
  showTrustRail?: boolean;
  showClueAction?: boolean;
  copy?: FeedCopy;
  companyCardCopy?: CompanyCardCopy;
}) {
  return (
    <section className="day-section">
      {showTitle ? <h2 className="day-title">{copy.tabs[bucket]}</h2> : null}
      <div className="company-list">
        {companies.map((company) => (
          <CompanyCard
            key={`${bucket}-${company.company}`}
            company={company}
            defaultVisibleJobs={defaultVisibleJobs}
            showJobExpand={showJobExpand}
            showTrustRail={showTrustRail}
            showClueAction={showClueAction}
            copy={companyCardCopy}
          />
        ))}
      </div>
    </section>
  );
}
