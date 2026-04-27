"use client";

import React, { useState } from "react";

import {
  AnimatedCard,
  CardBody,
  CardDescription,
  CardTitle,
  CardVisual,
  type ChartDatum,
  Visual3,
} from "./ui/animated-card-chart";
import LivingReportPaper from "./LivingReportPaper";
import type { IntelligencePayload } from "../lib/types";

type IntelligencePanelProps = {
  intelligence: IntelligencePayload;
  reportDateLabel: string;
  captureTitle: string;
  captureDescription: string;
  collectionStats: ChartDatum[];
};

export default function IntelligencePanel({
  intelligence,
  reportDateLabel,
  captureTitle,
  captureDescription,
  collectionStats,
}: IntelligencePanelProps) {
  const [showIntelPaper, setShowIntelPaper] = useState(false);
  const narrativeParagraphs = splitNarrativeIntoParagraphs(intelligence.narrative);
  const openIntelPaper = () => setShowIntelPaper(true);
  const closeIntelPaper = () => setShowIntelPaper(false);
  const handleIntelModeKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return;

    event.preventDefault();
    openIntelPaper();
  };

  return (
    <section className="intel-stage" aria-labelledby="intelligence-panel-title">
      <div className="intel-center-column">
        <div className="intel-card">
          <div className="intel-body">
            {showIntelPaper ? (
              <article
                className="intel-paper"
                aria-labelledby="intelligence-paper-title"
              >
                <button className="intel-back-button" type="button" onClick={closeIntelPaper}>
                  返回
                </button>
                <h2 id="intelligence-panel-title" className="intel-preview">
                  {intelligence.headline}
                </h2>
                <div className="intel-paper-copy">
                  <h3 id="intelligence-paper-title">{reportDateLabel}</h3>
                  {intelligence.living_report ? (
                    <LivingReportPaper report={intelligence.living_report} />
                  ) : (
                    narrativeParagraphs.map((paragraph, index) => (
                      <p key={`${index}-${paragraph}`} className="intel-narrative">
                        {paragraph}
                      </p>
                    ))
                  )}
                </div>
              </article>
            ) : (
              <AnimatedCard
                className="intel-chart-card is-clickable"
                aria-label="打开猎场控制台"
                aria-expanded={showIntelPaper}
                tabIndex={0}
                onClick={openIntelPaper}
                onKeyDown={handleIntelModeKeyDown}
              >
                <CardVisual>
                  <Visual3 data={collectionStats} mainColor="#75fb6e" secondaryColor="#26a17b" />
                </CardVisual>
                <CardBody>
                  <CardTitle id="intelligence-panel-title">{captureTitle}</CardTitle>
                  <CardDescription>{captureDescription}</CardDescription>
                </CardBody>
              </AnimatedCard>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}

function splitNarrativeIntoParagraphs(narrative: string) {
  const explicitParagraphs = narrative
    .split(/\n\s*\n/g)
    .map(collapseInlineWhitespace)
    .filter(Boolean);

  if (explicitParagraphs.length > 1) {
    return explicitParagraphs;
  }

  const normalized = collapseInlineWhitespace(narrative);
  if (!normalized) {
    return [];
  }

  return normalized.match(/[^。！？!?]+[。！？!?]?/g)?.map((sentence) => sentence.trim()).filter(Boolean) ?? [
    normalized,
  ];
}

function collapseInlineWhitespace(value: string) {
  return value.replace(/\s+/g, " ").trim();
}
