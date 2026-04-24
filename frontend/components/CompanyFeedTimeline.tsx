"use client";

import React, { useMemo, useState } from "react";

import CompanyDaySection from "./CompanyDaySection";
import type { DayBucketPayload } from "../lib/types";

export default function CompanyFeedTimeline({ days }: { days: DayBucketPayload[] }) {
  const [showEarlier, setShowEarlier] = useState(false);

  const { primaryDays, earlierDays } = useMemo(() => {
    const primary: DayBucketPayload[] = [];
    const earlier: DayBucketPayload[] = [];

    for (const day of days) {
      if (day.bucket === "today" || day.bucket === "yesterday") {
        primary.push(day);
      } else {
        earlier.push(day);
      }
    }

    return {
      primaryDays: primary,
      earlierDays: earlier,
    };
  }, [days]);

  return (
    <>
      {primaryDays.map((day) => (
        <CompanyDaySection key={day.bucket} bucket={day.bucket} companies={day.companies} />
      ))}

      {earlierDays.length ? (
        <div className="feed-more">
          <button
            type="button"
            className="feed-more-button"
            aria-expanded={showEarlier}
            onClick={() => setShowEarlier((value) => !value)}
          >
            {showEarlier ? "收起更早岗位" : "展开更早岗位"}
          </button>
        </div>
      ) : null}

      {showEarlier
        ? earlierDays.map((day, index) => (
            <CompanyDaySection key={`${day.bucket}-${index}`} bucket={day.bucket} companies={day.companies} />
          ))
        : null}
    </>
  );
}
