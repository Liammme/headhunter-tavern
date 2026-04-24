import React from "react";

import type { CompanyCardPayload, DayBucketPayload, IntelligencePayload } from "../lib/types";

type IntelligencePanelProps = {
  intelligence: IntelligencePayload;
  reportDateLabel: string;
  previewBucket: DayBucketPayload["bucket"] | null;
  previewCompanies: CompanyCardPayload[];
};

export default function IntelligencePanel({
  intelligence,
  reportDateLabel,
  previewBucket,
  previewCompanies,
}: IntelligencePanelProps) {
  const leadFinding = intelligence.findings[0];
  const secondaryFindings = intelligence.findings.slice(1, 3);
  const leadAction = intelligence.actions[0];
  const secondaryActions = intelligence.actions.slice(1, 3);

  return (
    <section className="intel-stage" aria-labelledby="intelligence-panel-title">
      <div className="intel-center-column">
        <div className="intel-card">
          <div className="intel-body">
            <article className="intel-paper" aria-labelledby="intelligence-paper-title">
              <div className="intel-paper-label-row">
                <p className="eyebrow intel-paper-label">猎场情报</p>
              </div>
              <h2 id="intelligence-panel-title" className="intel-preview">
                {intelligence.headline}
              </h2>
              <div className="intel-paper-copy">
                <h3 id="intelligence-paper-title">{reportDateLabel}</h3>
                <p className="intel-narrative">{intelligence.narrative}</p>
              </div>
            </article>
          </div>
        </div>
        <p className="intel-footnote">{intelligence.summary}</p>
        <section className="intel-peek-shell" aria-label="公司猎单池露头">
          <section className="intel-peek">
            <div className="intel-peek-copy">
              <p className="eyebrow">榜单露头</p>
              <h3>
                {previewBucket
                  ? `${renderBucketTitle(previewBucket)}的公司猎单池已经露头`
                  : "公司猎单池已经露头"}
              </h3>
              <p>下面就是今天的可操作机会池，往下滚就能直接进入公司档案卡。</p>
            </div>
            <div className="intel-peek-list">
              {previewCompanies.map((company) => (
                <article key={company.company} className="intel-peek-card">
                  <p className="intel-peek-company">{company.company}</p>
                  <p className="intel-peek-meta">
                    {renderCompanyGrade(company.company_grade)} · {company.total_jobs} 个岗位
                  </p>
                  <p className="intel-peek-claim">
                    {company.claimed_names.length
                      ? `已认领 ${company.claimed_names.join("、")}`
                      : "待认领"}
                  </p>
                </article>
              ))}
            </div>
          </section>
        </section>
      </div>
      <aside className="intel-notes" aria-label="侧栏注记">
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

function renderBucketTitle(bucket: DayBucketPayload["bucket"]) {
  if (bucket === "today") {
    return "今天";
  }
  if (bucket === "yesterday") {
    return "昨天";
  }
  return "更早";
}

function renderCompanyGrade(grade: CompanyCardPayload["company_grade"]) {
  if (grade === "focus") {
    return "重点公司";
  }
  if (grade === "watch") {
    return "关注公司";
  }
  return "普通公司";
}
