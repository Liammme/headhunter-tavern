"use client";

import React from "react";

import CompanyFeedTimeline from "./CompanyFeedTimeline";
import IntelligencePanel from "./IntelligencePanel";
import { JAPAN_UI_COPY } from "../lib/copy";
import type { ChartDatum } from "./ui/animated-card-chart";
import type { DayBucketPayload, IntelligencePayload } from "../lib/types";

type JapanHomeContentProps = {
  intelligence: IntelligencePayload;
  days: DayBucketPayload[];
  reportDateLabel: string;
  captureTitle: string;
  captureDescription: string;
  collectionStats: ChartDatum[];
};

export default function JapanHomeContent({
  intelligence,
  days,
  reportDateLabel,
  captureTitle,
  captureDescription,
  collectionStats,
}: JapanHomeContentProps) {
  const hasDays = days.length > 0;

  return (
    <>
      <IntelligencePanel
        intelligence={intelligence}
        reportDateLabel={reportDateLabel}
        captureTitle={captureTitle}
        captureDescription={captureDescription}
        collectionStats={collectionStats}
        copy={JAPAN_UI_COPY.intelligence}
        chartCopy={JAPAN_UI_COPY.chart}
      />

      <section className="feed-shell" aria-label="日本市場の求人リスト">
        {hasDays ? (
          <CompanyFeedTimeline
            days={days}
            showTrustRail={false}
            showClueAction={false}
            copy={JAPAN_UI_COPY.feed}
            companyCardCopy={JAPAN_UI_COPY.companyCard}
          />
        ) : (
          <section className="empty-state" aria-live="polite">
            <p className="eyebrow">Signal Status</p>
            <h2>表示できる求人はまだありません</h2>
            <p>取得タスクが完了すると、日本市場の独立データソースから取得した求人だけがここに表示されます。</p>
          </section>
        )}
      </section>
    </>
  );
}
