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
import type { IntelligencePayload } from "../lib/types";

type IntelligencePanelProps = {
  intelligence: IntelligencePayload;
  reportDateLabel: string;
  dailyCaptureSummary: string;
  collectionStats: ChartDatum[];
};

export default function IntelligencePanel({
  intelligence,
  reportDateLabel,
  dailyCaptureSummary,
  collectionStats,
}: IntelligencePanelProps) {
  const [showIntelPaper, setShowIntelPaper] = useState(false);
  const narrativeParagraphs = splitNarrativeIntoParagraphs(intelligence.narrative);
  const toggleIntelMode = () => setShowIntelPaper((value) => !value);
  const handleIntelModeKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return;

    event.preventDefault();
    toggleIntelMode();
  };

  return (
    <section className="intel-stage" aria-labelledby="intelligence-panel-title">
      <div className="intel-center-column">
        <div className="intel-card">
          <div className="intel-body">
            {showIntelPaper ? (
              <article
                className="intel-paper is-clickable"
                aria-labelledby="intelligence-paper-title"
                tabIndex={0}
                onClick={toggleIntelMode}
                onKeyDown={handleIntelModeKeyDown}
              >
                <div className="intel-paper-label-row">
                  <p className="eyebrow intel-paper-label">猎场控制台</p>
                </div>
                <h2 id="intelligence-panel-title" className="intel-preview">
                  {intelligence.headline}
                </h2>
                <div className="intel-paper-copy">
                  <h3 id="intelligence-paper-title">{reportDateLabel}</h3>
                  {narrativeParagraphs.map((paragraph, index) => (
                    <p key={`${index}-${paragraph}`} className="intel-narrative">
                      {paragraph}
                    </p>
                  ))}
                </div>
              </article>
            ) : (
              <AnimatedCard
                className="intel-chart-card is-clickable"
                aria-label="打开猎场控制台"
                aria-expanded={showIntelPaper}
                tabIndex={0}
                onClick={toggleIntelMode}
                onKeyDown={handleIntelModeKeyDown}
              >
                <CardVisual>
                  <Visual3 data={collectionStats} mainColor="#75fb6e" secondaryColor="#26a17b" />
                </CardVisual>
                <CardBody>
                  <CardTitle id="intelligence-panel-title">每日岗位收集数量</CardTitle>
                  <CardDescription>默认展示抓取节奏。需要看文字情报时，再切回猎场控制台。</CardDescription>
                </CardBody>
              </AnimatedCard>
            )}
          </div>
        </div>
        <p className="intel-footnote">{dailyCaptureSummary}</p>
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
