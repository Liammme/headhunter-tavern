"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";

import CompanyClaimSeal from "./CompanyClaimSeal";
import CompanyCluePanel from "./CompanyCluePanel";
import { requestCompanyClueLetter } from "../lib/api";
import type { CompanyCardPayload, CompanyClueResponse, CompanyClueState, JobCardPayload } from "../lib/types";

export default function CompanyCard({
  company,
  defaultVisibleJobs = 3,
  showJobExpand = true,
}: {
  company: CompanyCardPayload;
  defaultVisibleJobs?: number;
  showJobExpand?: boolean;
}) {
  const [companyState, setCompanyState] = useState(company);
  const [expanded, setExpanded] = useState(false);
  const [isClueOpen, setIsClueOpen] = useState(false);
  const [clueState, setClueState] = useState<CompanyClueState | null>(null);
  const clueRequestIdRef = useRef(0);

  useEffect(() => {
    setCompanyState(company);
    setIsClueOpen(false);
    setClueState(null);
  }, [company]);

  const jobs = useMemo(() => {
    if (expanded) {
      return companyState.jobs;
    }
    return companyState.jobs.slice(0, defaultVisibleJobs);
  }, [companyState.jobs, defaultVisibleJobs, expanded]);

  function handleClaimCreated(jobId: number, claimerName: string) {
    setCompanyState((current) => {
      const normalizedName = claimerName.trim();
      if (!normalizedName) {
        return current;
      }

      return {
        ...current,
        claimed_by: current.claimed_by ?? normalizedName,
        claim_status: "已签署",
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

  const claimJob = companyState.jobs[0]
    ? {
        ...companyState.jobs[0],
        claimed_names: companyState.claimed_names,
      }
    : null;

  function handleSealClaimCreated(claimerName: string) {
    if (!claimJob) {
      return;
    }

    handleClaimCreated(claimJob.id, claimerName);
  }

  async function requestClueLetter() {
    const requestId = clueRequestIdRef.current + 1;
    clueRequestIdRef.current = requestId;
    setIsClueOpen(true);
    setClueState({
      status: "loading",
      company: companyState.company,
      generated_at: new Date().toISOString(),
      narrative: "",
      sections: [],
      error_message: null,
    });

    try {
      const response = await requestCompanyClueLetter({ company: companyState.company });
      if (clueRequestIdRef.current !== requestId) {
        return;
      }
      setClueState(normalizeClueResponse(response));
    } catch {
      if (clueRequestIdRef.current !== requestId) {
        return;
      }
      setClueState({
        status: "failure",
        company: companyState.company,
        generated_at: new Date().toISOString(),
        narrative: `${companyState.company} 的单公司线索来信生成失败，请稍后重试。`,
        sections: [],
        error_message: "Failed to request company clue letter",
      });
    }
  }

  async function handleClueToggle() {
    if (isClueOpen) {
      setIsClueOpen(false);
      return;
    }

    await requestClueLetter();
  }

  return (
    <article className="company-card">
      <div className="company-top">
        <div className="company-dossier-head">
          <h3>
            {companyState.company_url ? (
              <a href={companyState.company_url} target="_blank" rel="noreferrer">
                {companyState.company}
              </a>
            ) : (
              companyState.company
            )}
          </h3>
          <div className="company-meta">
            <span>共 {companyState.total_jobs} 个岗位</span>
            <span>已认领 {companyState.claimed_names.length} 人</span>
          </div>
          <div className="company-actions">
            <button
              type="button"
              className="company-clue-tag"
              aria-label={isClueOpen ? "收起线索" : "线索"}
              aria-expanded={isClueOpen}
              onClick={handleClueToggle}
            >
              <span className="company-clue-icon" aria-hidden="true">
                <svg viewBox="0 0 16 16" focusable="false">
                  <circle cx="7" cy="7" r="4.25" fill="none" stroke="currentColor" strokeWidth="2.5" />
                  <path d="M10.4 10.4L13.5 13.5" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
                </svg>
              </span>
              <span>线索</span>
            </button>
            <span className="company-grade">{renderCompanyGrade(companyState.company_grade)}</span>
          </div>
          {companyState.jd_trust ? <JdTrustSummary jdTrust={companyState.jd_trust} /> : null}
        </div>
        <CompanyClaimSeal company={companyState} claimJob={claimJob} onClaimCreated={handleSealClaimCreated} />
      </div>
      {isClueOpen && clueState ? (
        <CompanyCluePanel
          clue={clueState}
          onRetry={clueState.status === "failure" ? requestClueLetter : undefined}
          onClose={() => setIsClueOpen(false)}
        />
      ) : null}
      <section className="job-list" aria-label={`${companyState.company}在招岗位`}>
        {jobs.map((job) => (
          <div key={job.id} className="job-row">
            <div>
              <h4 className="job-title">{job.title}</h4>
              <div className="job-evidence">
                <div className="job-badges">
                  {job.tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="job-badge">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <div className="job-actions">
              <a href={job.canonical_url} target="_blank" rel="noreferrer">
                查看原帖
              </a>
            </div>
          </div>
        ))}
      </section>
      {showJobExpand && companyState.jobs.length > defaultVisibleJobs ? (
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

function JdTrustSummary({ jdTrust }: { jdTrust: NonNullable<CompanyCardPayload["jd_trust"]> }) {
  const checks = jdTrust.recommended_checks.slice(0, 2);

  return (
    <section className="jdtrust-summary" aria-label="JD可信度甄别结果">
      <div className="jdtrust-heading">
        <span className={`jdtrust-risk jdtrust-risk-${jdTrust.risk_level}`}>JD可信度：{renderJdTrustRisk(jdTrust.risk_level)}</span>
        {typeof jdTrust.trust_score === "number" ? (
          <span className="jdtrust-score">
            可信度分 <strong>{jdTrust.trust_score}</strong>
          </span>
        ) : null}
      </div>
      {checks.length ? (
        <ul className="jdtrust-checks">
          {checks.map((check) => (
            <li key={check}>{check}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function renderJdTrustRisk(riskLevel: NonNullable<CompanyCardPayload["jd_trust"]>["risk_level"]) {
  if (riskLevel === "high") {
    return "高风险";
  }
  if (riskLevel === "needs_review") {
    return "需核验";
  }
  return "较可信";
}

function appendClaimer(claimedNames: JobCardPayload["claimed_names"], claimerName: string) {
  return claimedNames.includes(claimerName) ? claimedNames : [...claimedNames, claimerName];
}

function normalizeClueResponse(response: CompanyClueResponse): CompanyClueState {
  if (response.status === "loading") {
    return {
      status: "loading",
      company: response.company,
      generated_at: response.generated_at,
      narrative: response.narrative,
      sections: response.sections,
      error_message: null,
    };
  }

  return {
    status: response.status,
    company: response.company,
    generated_at: response.generated_at,
    narrative: response.narrative,
    sections: response.sections,
    error_message: response.error_message ?? null,
  };
}
