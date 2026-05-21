import React from "react";

import { DEFAULT_LIVING_REPORT_COPY, type LivingReportCopy } from "../lib/copy";
import type { LivingReportPayload } from "../lib/types";

type LivingReportPaperProps = {
  report: LivingReportPayload;
  copy?: LivingReportCopy;
};

export default function LivingReportPaper({ report, copy = DEFAULT_LIVING_REPORT_COPY }: LivingReportPaperProps) {
  return (
    <div className="living-report-scroll">
      <header className="living-report-header">
        <div className="living-report-meta" aria-label={copy.metaAriaLabel}>
          <span>{copy.versionLabel(report.version)}</span>
          <span>{copy.baselineLabel(report.seed_window_days)}</span>
          <span>{copy.updatedLabel(report.generated_at)}</span>
        </div>
        <h3 className="living-report-title">{report.headline}</h3>
        <div className="living-report-copy">
          {renderTextBlocks(report.executive_summary)}
        </div>
      </header>

      <section className="living-report-sections" aria-label={copy.sectionsAriaLabel}>
        {report.sections.length > 0 ? (
          report.sections.map((section) => (
            <section key={section.section_id} className="living-report-section">
              <h3>{section.title}</h3>
              <div className="living-report-copy">{renderTextBlocks(section.body)}</div>
            </section>
          ))
        ) : (
          <p className="living-report-empty">{copy.emptySectionsLabel}</p>
        )}
      </section>

      <section className="living-report-claims" aria-label={copy.claimsAriaLabel}>
        <h3>{copy.claimsTitle}</h3>
        <ul>
          {report.claims.map((claim) => (
            <li key={claim.claim_id}>
              <span className="living-report-claim-status">{copy.statusLabels[claim.status] ?? claim.status}</span>
              <strong>{claim.claim}</strong>
              <small>{claim.confidence} confidence · {claim.evidence_ids.join(", ")}</small>
            </li>
          ))}
        </ul>
      </section>

      <section className="living-report-watchlist" aria-label={copy.watchlistAriaLabel}>
        <h3>{copy.watchlistTitle}</h3>
        {report.watchlist.map((item) => (
          <p key={`${item.topic}-${item.why_watch}`}>
            <strong>{item.topic}</strong>
            <span>{item.why_watch}</span>
          </p>
        ))}
      </section>

      <footer className="living-report-quality">
        <span>{copy.sampleCountLabel(report.data_quality.sample_count ?? 0)}</span>
        {report.data_quality.baseline_note ? <span>{report.data_quality.baseline_note}</span> : null}
      </footer>
    </div>
  );
}

function renderTextBlocks(value: string) {
  return value
    .split(/\n\s*\n/g)
    .map((block) => block.replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .map((block) => <p key={block}>{block}</p>);
}
