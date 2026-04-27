import React from "react";

import type { LivingReportPayload } from "../lib/types";

type LivingReportPaperProps = {
  report: LivingReportPayload;
};

const STATUS_LABELS: Record<string, string> = {
  new: "新增",
  reinforced: "强化",
  weakened: "削弱",
  retired: "退休",
};

export default function LivingReportPaper({ report }: LivingReportPaperProps) {
  return (
    <div className="living-report-scroll">
      <header className="living-report-header">
        <div className="living-report-meta" aria-label="活报告元信息">
          <span>第 {report.version} 版</span>
          <span>基于 {report.seed_window_days} 天基线</span>
          <span>最近更新 {report.generated_at}</span>
        </div>
        <h3 className="living-report-title">{report.headline}</h3>
        <div className="living-report-copy">
          {renderTextBlocks(report.executive_summary)}
        </div>
      </header>

      <section className="living-report-sections" aria-label="报告章节">
        {report.sections.length > 0 ? (
          report.sections.map((section) => (
            <section key={section.section_id} className="living-report-section">
              <h3>{section.title}</h3>
              <div className="living-report-copy">{renderTextBlocks(section.body)}</div>
            </section>
          ))
        ) : (
          <p className="living-report-empty">暂无可展示章节。</p>
        )}
      </section>

      <section className="living-report-claims" aria-label="报告判断">
        <h3>判断</h3>
        <ul>
          {report.claims.map((claim) => (
            <li key={claim.claim_id}>
              <span className="living-report-claim-status">{STATUS_LABELS[claim.status] ?? claim.status}</span>
              <strong>{claim.claim}</strong>
              <small>{claim.confidence} confidence · {claim.evidence_ids.join(", ")}</small>
            </li>
          ))}
        </ul>
      </section>

      <section className="living-report-watchlist" aria-label="观察清单">
        <h3>观察清单</h3>
        {report.watchlist.map((item) => (
          <p key={`${item.topic}-${item.why_watch}`}>
            <strong>{item.topic}</strong>
            <span>{item.why_watch}</span>
          </p>
        ))}
      </section>

      <footer className="living-report-quality">
        <span>样本数 {report.data_quality.sample_count ?? 0}</span>
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
