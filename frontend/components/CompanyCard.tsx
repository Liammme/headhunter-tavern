"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";

import CompanyClaimSeal from "./CompanyClaimSeal";
import CompanyCluePanel from "./CompanyCluePanel";
import { requestCompanyClueLetter } from "../lib/api";
import type { CompanyCardPayload, CompanyClueResponse, CompanyClueState } from "../lib/types";

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
        </div>
        <CompanyClaimSeal company={companyState} />
      </div>
      {isClueOpen && clueState ? (
        <CompanyCluePanel
          clue={clueState}
          onRetry={clueState.status === "failure" ? requestClueLetter : undefined}
          onClose={() => setIsClueOpen(false)}
        />
      ) : null}
      <section className="job-list" aria-label={`${companyState.company}在招岗位`}>
        {jobs.map((job) => {
          const verificationTags = job.verification_tags ?? [];
          return (
            <div key={job.id} className="job-row">
              <div>
                <h4 className="job-title">{job.title}</h4>
                {verificationTags.length > 0 ? (
                  <div className="job-evidence">
                    <div className="job-badges">
                      {verificationTags.slice(0, 4).map((tag) => (
                        <span
                          key={`${tag.tone}-${tag.label}`}
                          className={`job-badge job-badge-${tag.tone}`}
                          tabIndex={0}
                        >
                          {tag.label}
                          <span className="job-badge-tooltip" role="tooltip">
                            {tag.description}
                          </span>
                        </span>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
              <div className="job-actions">
                <a href={job.canonical_url} target="_blank" rel="noreferrer">
                  查看原帖
                </a>
              </div>
            </div>
          );
        })}
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
