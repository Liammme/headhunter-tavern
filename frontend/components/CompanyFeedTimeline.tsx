"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";

import CompanyDaySection from "./CompanyDaySection";
import { AnimatedTabs } from "./ui/animated-tabs";
import { DEFAULT_FEED_COPY, type CompanyCardCopy, type FeedCopy } from "../lib/copy";
import {
  JOB_CATEGORY_OPTIONS,
  type CompanyCardPayload,
  type DayBucketPayload,
  type JobCategory,
} from "../lib/types";

const FEED_TABS: Array<{ bucket: DayBucketPayload["bucket"] }> = [
  { bucket: "within_3_days" },
  { bucket: "within_7_days" },
  { bucket: "earlier" },
];

const EARLIER_JOB_PREVIEW_LIMIT = 10;

export default function CompanyFeedTimeline({
  days,
  showTrustRail = true,
  showClueAction = true,
  copy = DEFAULT_FEED_COPY,
  companyCardCopy,
}: {
  days: DayBucketPayload[];
  showTrustRail?: boolean;
  showClueAction?: boolean;
  copy?: FeedCopy;
  companyCardCopy?: CompanyCardCopy;
}) {
  const [activeBucket, setActiveBucket] = useState<DayBucketPayload["bucket"]>("within_3_days");
  const [selectedCategories, setSelectedCategories] = useState<JobCategory[]>([]);
  const [categoryPanelOpen, setCategoryPanelOpen] = useState(false);
  const [showAllEarlier, setShowAllEarlier] = useState(false);
  const categoryFilterRef = useRef<HTMLDivElement>(null);

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

  const activeCompanies = daysByBucket[activeBucket];
  const filteredCompanies = filterCompaniesByCategory(activeCompanies, selectedCategories);
  const categoryActionLabel = formatCategoryActionLabel(selectedCategories, copy);
  const isEarlier = activeBucket === "earlier";
  const { companies: visibleCompanies, hasHiddenJobs } =
    isEarlier && !showAllEarlier
      ? limitCompaniesByJobs(filteredCompanies, EARLIER_JOB_PREVIEW_LIMIT)
      : { companies: filteredCompanies, hasHiddenJobs: false };

  useEffect(() => {
    if (!categoryPanelOpen) {
      return;
    }

    const closeOnOutsidePointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (target instanceof Node && categoryFilterRef.current?.contains(target)) {
        return;
      }

      setCategoryPanelOpen(false);
    };

    document.addEventListener("pointerdown", closeOnOutsidePointerDown);
    return () => document.removeEventListener("pointerdown", closeOnOutsidePointerDown);
  }, [categoryPanelOpen]);

  return (
    <div className="feed-timeline">
      <div className="feed-tabs-row" ref={categoryFilterRef}>
        <AnimatedTabs
          tabs={FEED_TABS.map(({ bucket }) => ({ label: copy.tabs[bucket] }))}
          activeLabel={copy.tabs[activeBucket]}
          actions={[
            {
              label: categoryActionLabel,
              active: selectedCategories.length > 0 || categoryPanelOpen,
              ariaExpanded: categoryPanelOpen,
              ariaControls: "job-category-filter-panel",
              onClick: () => setCategoryPanelOpen((value) => !value),
            },
          ]}
          ariaLabel={copy.ariaLabel}
          logoSrc="/q.svg"
          logoAlt={copy.logoAlt}
          onChange={(label) => {
            const selected = FEED_TABS.find((tab) => copy.tabs[tab.bucket] === label);
            setActiveBucket(selected?.bucket ?? "within_3_days");
            setShowAllEarlier(false);
            setCategoryPanelOpen(false);
          }}
        />

        {categoryPanelOpen ? (
          <div id="job-category-filter-panel" className="job-category-filter-panel" aria-label={copy.categoryFilterAriaLabel}>
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
                  {copy.categoryLabels[category]}
                </button>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      {visibleCompanies.length ? (
        <CompanyDaySection
          bucket={activeBucket}
          companies={visibleCompanies}
          showTitle={false}
          defaultVisibleJobs={isEarlier ? Number.MAX_SAFE_INTEGER : undefined}
          showJobExpand={!isEarlier}
          showTrustRail={showTrustRail}
          showClueAction={showClueAction}
          copy={copy}
          companyCardCopy={companyCardCopy}
        />
      ) : (
        <section className="empty-state" aria-live="polite">
          <p className="eyebrow">{copy.tabs[activeBucket]}</p>
          <h2>{selectedCategories.length ? copy.emptyNoMatchTitle : copy.emptyNoJobsTitle}</h2>
          <p>{copy.emptyDescription}</p>
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
            {showAllEarlier ? copy.collapseEarlierLabel : copy.expandEarlierLabel}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function formatCategoryActionLabel(categories: JobCategory[], copy: FeedCopy): string {
  if (!categories.length) {
    return copy.allCategoriesLabel;
  }

  const label = categories.map((category) => copy.categoryLabels[category]).join("/");
  if (label.length <= 5) {
    return label;
  }

  return `${label.slice(0, 4)}..`;
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
