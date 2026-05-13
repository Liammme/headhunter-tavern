"use client";

import React, { useMemo, useState } from "react";

import CompanyDaySection from "./CompanyDaySection";
import { AnimatedTabs } from "./ui/animated-tabs";
import {
  JOB_CATEGORY_OPTIONS,
  type CompanyCardPayload,
  type DayBucketPayload,
  type JobCategory,
} from "../lib/types";

const FEED_TABS: Array<{ label: FeedTabLabel; bucket: DayBucketPayload["bucket"] }> = [
  { label: "最新", bucket: "within_3_days" },
  { label: "7天内", bucket: "within_7_days" },
  { label: "更早", bucket: "earlier" },
];

const EARLIER_JOB_PREVIEW_LIMIT = 10;

type FeedTabLabel = "最新" | "7天内" | "更早";

export default function CompanyFeedTimeline({ days }: { days: DayBucketPayload[] }) {
  const [activeTab, setActiveTab] = useState<FeedTabLabel>("最新");
  const [selectedCategories, setSelectedCategories] = useState<JobCategory[]>([]);
  const [categoryPanelOpen, setCategoryPanelOpen] = useState(false);
  const [showAllEarlier, setShowAllEarlier] = useState(false);

  const daysByBucket = useMemo(() => {
    const grouped: Record<DayBucketPayload["bucket"], CompanyCardPayload[]> = {
      within_3_days: [],
      within_7_days: [],
      earlier: [],
    };

    for (const day of days) {
      grouped[day.bucket].push(...day.companies);
    }

    return grouped;
  }, [days]);

  const activeBucket = FEED_TABS.find((tab) => tab.label === activeTab)?.bucket ?? "within_3_days";
  const activeCompanies = daysByBucket[activeBucket];
  const filteredCompanies = filterCompaniesByCategory(activeCompanies, selectedCategories);
  const isEarlier = activeBucket === "earlier";
  const { companies: visibleCompanies, hasHiddenJobs } =
    isEarlier && !showAllEarlier
      ? limitCompaniesByJobs(filteredCompanies, EARLIER_JOB_PREVIEW_LIMIT)
      : { companies: filteredCompanies, hasHiddenJobs: false };

  return (
    <div className="feed-timeline">
      <div className="feed-tabs-row">
        <AnimatedTabs
          tabs={FEED_TABS.map(({ label }) => ({ label }))}
          activeLabel={activeTab}
          actions={[
            {
              label: selectedCategories.length ? `已选 ${selectedCategories.length}` : "全部岗位",
              active: selectedCategories.length > 0 || categoryPanelOpen,
              ariaExpanded: categoryPanelOpen,
              ariaControls: "job-category-filter-panel",
              onClick: () => setCategoryPanelOpen((value) => !value),
            },
          ]}
          ariaLabel="岗位时间筛选"
          logoSrc="/q.svg"
          logoAlt="赏金猎人"
          onChange={(label) => {
            setActiveTab(label as FeedTabLabel);
            setShowAllEarlier(false);
            setCategoryPanelOpen(false);
          }}
        />

        {categoryPanelOpen ? (
          <div id="job-category-filter-panel" className="job-category-filter-panel" aria-label="岗位类型筛选">
            <div className="job-category-filter-head">
              <button
                type="button"
                className="job-category-filter-clear"
                disabled={!selectedCategories.length}
                onClick={() => {
                  setSelectedCategories([]);
                  setShowAllEarlier(false);
                }}
              >
                清空
              </button>
            </div>
            <div className="job-category-options">
              {JOB_CATEGORY_OPTIONS.map((category) => (
                <button
                  key={category}
                  type="button"
                  className={`job-category-option${selectedCategories.includes(category) ? " job-category-option-selected" : ""}`}
                  aria-pressed={selectedCategories.includes(category)}
                  onClick={() => {
                    setSelectedCategories((current) => toggleCategory(current, category));
                    setShowAllEarlier(false);
                  }}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      {selectedCategories.length ? (
        <div className="job-category-active-list" aria-label="已选择岗位类型">
          {selectedCategories.map((category) => (
            <button
              key={category}
              type="button"
              className="job-category-active-chip"
              aria-label={`移除${category}筛选`}
              onClick={() => {
                setSelectedCategories((current) => current.filter((item) => item !== category));
                setShowAllEarlier(false);
              }}
            >
              {category}
              <span aria-hidden="true">×</span>
            </button>
          ))}
        </div>
      ) : null}

      {visibleCompanies.length ? (
        <CompanyDaySection
          bucket={activeBucket}
          companies={visibleCompanies}
          showTitle={false}
          defaultVisibleJobs={isEarlier ? Number.MAX_SAFE_INTEGER : undefined}
          showJobExpand={!isEarlier}
        />
      ) : (
        <section className="empty-state" aria-live="polite">
          <p className="eyebrow">{activeTab}</p>
          <h2>{selectedCategories.length ? "这一栏暂时没有匹配岗位" : "这一栏暂时没有岗位"}</h2>
          <p>等下一次抓取写入后，这里会自动展示对应时间段的公司机会。</p>
        </section>
      )}

      {isEarlier && (hasHiddenJobs || showAllEarlier) ? (
        <div className="feed-more feed-more-bottom">
          <button
            type="button"
            className="feed-more-button"
            aria-expanded={showAllEarlier}
            onClick={() => setShowAllEarlier((value) => !value)}
          >
            {showAllEarlier ? "收起更早岗位" : "展开全部更早岗位"}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function toggleCategory(current: JobCategory[], category: JobCategory): JobCategory[] {
  if (current.includes(category)) {
    return current.filter((item) => item !== category);
  }

  return [...current, category];
}

function filterCompaniesByCategory(companies: CompanyCardPayload[], categories: JobCategory[]): CompanyCardPayload[] {
  if (!categories.length) {
    return companies;
  }

  return companies.flatMap((company) => {
    const jobs = company.jobs.filter((job) => categories.includes(job.job_category));
    if (!jobs.length) {
      return [];
    }

    return [
      {
        ...company,
        total_jobs: jobs.length,
        jobs,
      },
    ];
  });
}

function limitCompaniesByJobs(companies: CompanyCardPayload[], maxJobs: number) {
  const visible: CompanyCardPayload[] = [];
  let remainingJobs = maxJobs;
  let hasHiddenJobs = false;

  for (const company of companies) {
    if (remainingJobs <= 0) {
      hasHiddenJobs = true;
      break;
    }

    if (company.jobs.length <= remainingJobs) {
      visible.push(company);
      remainingJobs -= company.jobs.length;
      continue;
    }

    visible.push({
      ...company,
      jobs: company.jobs.slice(0, remainingJobs),
    });
    hasHiddenJobs = true;
    remainingJobs = 0;
  }

  return { companies: visible, hasHiddenJobs };
}
