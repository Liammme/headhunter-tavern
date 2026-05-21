"use client";

import React from "react";

import IntelligencePanel from "./IntelligencePanel";
import { JAPAN_UI_COPY } from "../lib/copy";
import type { ChartDatum } from "./ui/animated-card-chart";
import type { IntelligencePayload } from "../lib/types";

type JapanHomeContentProps = {
  intelligence: IntelligencePayload;
  reportDateLabel: string;
  captureTitle: string;
  captureDescription: string;
  collectionStats: ChartDatum[];
};

export default function JapanHomeContent({
  intelligence,
  reportDateLabel,
  captureTitle,
  captureDescription,
  collectionStats,
}: JapanHomeContentProps) {
  return (
    <IntelligencePanel
      intelligence={intelligence}
      reportDateLabel={reportDateLabel}
      captureTitle={captureTitle}
      captureDescription={captureDescription}
      collectionStats={collectionStats}
      copy={JAPAN_UI_COPY.intelligence}
      chartCopy={JAPAN_UI_COPY.chart}
    />
  );
}
