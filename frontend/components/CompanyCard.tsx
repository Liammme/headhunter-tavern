"use client";

import { useEffect, useMemo, useState } from "react";

import ClaimDialog from "./ClaimDialog";
import type { CompanyCardPayload, JobCardPayload } from "../lib/types";

export default function CompanyCard({ company }: { company: CompanyCardPayload }) {
  const [companyState, setCompanyState] = useState(company);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    setCompanyState(company);
  }, [company]);

  const jobs = useMemo(() => {
    if (expanded) {
      return companyState.jobs;
    }
    return companyState.jobs.slice(0, 3);
  }, [companyState.jobs, expanded]);

  function handleClaimCreated(jobId: number, claimerName: string) {
    setCompanyState((current) => {
      const normalizedName = claimerName.trim();
      if (!normalizedName) {
        return current;
      }

      return {
        ...current,
        claimed_names: appendClaimer(current.claimed_names, normalizedName),
        jobs: current.jobs.map((job) =>
          job.id === jobId
            ? {
                ...job,
                claimed_names: appendClaimer(job.claimed_names, normalizedName),
              }
            : job,
        ),
      };
    });
  }

  return (
    <article className="company-card">
      <div className="company-top">
        <div>
          <h3>{companyState.company}</h3>
          <div className="company-meta">
            <span className="company-grade">{renderCompanyGrade(companyState.company_grade)}</span>
            <span>共 {companyState.total_jobs} 个岗位</span>
          </div>
        </div>
        <div className="job-claims">
          <span>已认领：</span>
          <span>{companyState.claimed_names.length ? companyState.claimed_names.join("、") : "暂无"}</span>
        </div>
      </div>
      <div className="job-list">
        {jobs.map((job) => (
          <div key={job.id} className="job-row">
            <div>
              <h4 className="job-title">{job.title}</h4>
              <div className="job-badges">
                <span className="job-badge">{renderBountyGrade(job.bounty_grade)}</span>
                {job.tags.slice(0, 3).map((tag) => (
                  <span key={tag} className="job-badge">
                    {tag}
                  </span>
                ))}
              </div>
              <div className="job-claims">
                <span>已认领：</span>
                <span>{job.claimed_names.length ? job.claimed_names.join("、") : "暂无"}</span>
              </div>
            </div>
            <div className="job-actions">
              <a href={job.canonical_url} target="_blank" rel="noreferrer">
                查看原帖
              </a>
              <ClaimDialog job={job} onClaimCreated={(claimerName) => handleClaimCreated(job.id, claimerName)} />
            </div>
          </div>
        ))}
      </div>
      {companyState.jobs.length > 3 ? (
        <div className="company-footer">
          <button type="button" onClick={() => setExpanded((value) => !value)}>
            {expanded ? "收起岗位" : "展开更多岗位"}
          </button>
        </div>
      ) : null}
    </article>
  );
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

function renderBountyGrade(grade: CompanyCardPayload["jobs"][number]["bounty_grade"]) {
  if (grade === "high") {
    return "高赏金";
  }
  if (grade === "medium") {
    return "中赏金";
  }
  return "低赏金";
}

function appendClaimer(claimedNames: JobCardPayload["claimed_names"], claimerName: string) {
  return claimedNames.includes(claimerName) ? claimedNames : [...claimedNames, claimerName];
}
