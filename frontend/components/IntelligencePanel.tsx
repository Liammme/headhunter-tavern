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
  const leadFinding = intelligence.findings[0];
  const secondaryFindings = intelligence.findings.slice(1, 3);
  const leadAction = intelligence.actions[0];
  const secondaryActions = intelligence.actions.slice(1, 3);
  const narrativeParagraphs = splitNarrativeIntoParagraphs(intelligence.narrative);

  return (
    <section className="intel-stage" aria-labelledby="intelligence-panel-title">
      <div className="intel-center-column">
        <div className="intel-card">
          <div className="intel-body">
            {showIntelPaper ? (
              <article className="intel-paper" aria-labelledby="intelligence-paper-title">
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
              <AnimatedCard className="intel-chart-card" aria-labelledby="intelligence-panel-title">
                <CardVisual>
                  <Visual3 data={collectionStats} mainColor="#75fb6e" secondaryColor="#26a17b" />
                </CardVisual>
                <CardBody>
                  <p className="eyebrow intel-paper-label">猎场控制台</p>
                  <CardTitle id="intelligence-panel-title">每日岗位收集数量</CardTitle>
                  <CardDescription>默认展示抓取节奏。需要看文字情报时，再切回猎场控制台。</CardDescription>
                </CardBody>
              </AnimatedCard>
            )}
          </div>
        </div>
        <button
          type="button"
          className="intel-mode-toggle"
          aria-expanded={showIntelPaper}
          onClick={() => setShowIntelPaper((value) => !value)}
        >
          {showIntelPaper ? "返回岗位统计" : "查看猎场控制台"}
        </button>
        <p className="intel-footnote">{dailyCaptureSummary}</p>
      </div>
      <aside className="intel-notes" aria-label="今日行动信号">
        <div className="intel-note-grid">
          <section
            className="intel-note-card intel-note-card-highlight"
            aria-labelledby="intelligence-findings-title"
          >
            <span className="intel-note-badge" aria-hidden="true">
              ☆
            </span>
            <h4 id="intelligence-findings-title">情报发现</h4>
            {leadFinding ? <p>{leadFinding}</p> : <p>暂无新增发现。</p>}
            {secondaryFindings.length ? (
              <ul>
                {secondaryFindings.map((finding) => (
                  <li key={finding}>{finding}</li>
                ))}
              </ul>
            ) : null}
          </section>
          <section className="intel-note-card" aria-labelledby="intelligence-actions-title">
            <span className="intel-note-badge" aria-hidden="true">
              ☆
            </span>
            <h4 id="intelligence-actions-title">跟进动作</h4>
            {leadAction ? (
              <p className="intel-action-lead">{leadAction}</p>
            ) : (
              <p className="intel-action-lead">暂无跟进动作。</p>
            )}
            {secondaryActions.length ? (
              <ul>
                {secondaryActions.map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            ) : null}
          </section>
        </div>
      </aside>
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
