import React from "react";

import type { CompanyCardPayload, DayBucketPayload, IntelligencePayload } from "../lib/types";

type IntelligencePanelProps = {
  intelligence: IntelligencePayload;
  previewBucket: DayBucketPayload["bucket"] | null;
  previewCompanies: CompanyCardPayload[];
};

export default function IntelligencePanel({
  intelligence,
  previewBucket,
  previewCompanies,
}: IntelligencePanelProps) {
  return (
    <section className="intel-card" aria-labelledby="intelligence-panel-title">
      <div className="intel-head">
        <div>
          <p className="eyebrow">猎场情报</p>
          <h2 id="intelligence-panel-title" className="intel-preview">
            {intelligence.headline}
          </h2>
        </div>
        <p className="intel-footnote">基于近 14 天岗位池与历史轻量统计生成</p>
      </div>
      <div className="intel-body">
        <article aria-labelledby="intelligence-paper-title">
          <p className="eyebrow">纸页正文</p>
          <h3 id="intelligence-paper-title">{intelligence.summary}</h3>
          <p className="intel-narrative">{intelligence.narrative}</p>
        </article>
        <aside aria-labelledby="intelligence-notes-title">
          <p className="eyebrow">侧栏注记</p>
          <h3 id="intelligence-notes-title">行动注记</h3>
          <section aria-labelledby="intelligence-findings-title">
            <h4 id="intelligence-findings-title">情报发现</h4>
            <ul>
              {intelligence.findings.map((finding) => (
                <li key={finding}>{finding}</li>
              ))}
            </ul>
          </section>
          <section aria-labelledby="intelligence-actions-title">
            <h4 id="intelligence-actions-title">跟进动作</h4>
            <ul>
              {intelligence.actions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </section>
        </aside>
      </div>

      <section className="intel-peek" aria-label="公司猎单池露头">
        <div className="intel-peek-copy">
          <p className="eyebrow">榜单露头</p>
          <h3>{previewBucket ? `${renderBucketTitle(previewBucket)}的公司猎单池已经露头` : "公司猎单池已经露头"}</h3>
          <p>下面就是今天的可操作机会池，往下滚就能直接进入公司档案卡。</p>
        </div>
        <div className="intel-peek-list">
          {previewCompanies.map((company) => (
            <article key={company.company} className="intel-peek-card">
              <p className="intel-peek-company">{company.company}</p>
              <p className="intel-peek-meta">
                {renderCompanyGrade(company.company_grade)} · {company.total_jobs} 个岗位
              </p>
            </article>
          ))}
        </div>
      </section>
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
