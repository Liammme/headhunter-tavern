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
const ALL_CATEGORY_LABEL = "全部";

type FeedTabLabel = "最新" | "7天内" | "更早";
type JobCategoryFilter = typeof ALL_CATEGORY_LABEL | JobCategory;
const CATEGORY_FILTER_OPTIONS: JobCategoryFilter[] = [ALL_CATEGORY_LABEL, ...JOB_CATEGORY_OPTIONS];

export default function CompanyFeedTimeline({ days }: { days: DayBucketPayload[] }) {
  const [activeTab, setActiveTab] = useState<FeedTabLabel>("最新");
  const [activeCategory, setActiveCategory] = useState<JobCategoryFilter>(ALL_CATEGORY_LABEL);
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
  const filteredCompanies = filterCompaniesByCategory(activeCompanies, activeCategory);
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
          ariaLabel="岗位时间筛选"
          logoSrc="/q.svg"
          logoAlt="赏金猎人"
          onChange={(label) => {
            setActiveTab(label as FeedTabLabel);
            setShowAllEarlier(false);
          }}
        />
      </div>

      <div className="job-category-filter-row" aria-label="岗位类型筛选">
        {CATEGORY_FILTER_OPTIONS.map((category) => (
          <button
            key={category}
            type="button"
            className="job-category-chip"
            aria-pressed={activeCategory === category}
            onClick={() => {
              setActiveCategory(category);
              setShowAllEarlier(false);
            }}
          >
            {category}
          </button>
        ))}
      </div>

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
          <h2>
            {activeCategory === ALL_CATEGORY_LABEL ? "这一栏暂时没有岗位" : `这一栏暂时没有${activeCategory}岗位`}
          </h2>
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

function filterCompaniesByCategory(companies: CompanyCardPayload[], category: JobCategoryFilter): CompanyCardPayload[] {
  if (category === ALL_CATEGORY_LABEL) {
    return companies;
  }

  return companies.flatMap((company) => {
    const jobs = company.jobs.filter((job) => job.job_category === category);
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
