"use client";

import React, { useMemo, useState } from "react";

import CompanyDaySection from "./CompanyDaySection";
import { AnimatedTabs } from "./ui/animated-tabs";
import type { CompanyCardPayload, DayBucketPayload } from "../lib/types";

const FEED_TABS: Array<{ label: FeedTabLabel; bucket: DayBucketPayload["bucket"] }> = [
  { label: "今天", bucket: "today" },
  { label: "昨天", bucket: "yesterday" },
  { label: "更早", bucket: "earlier" },
];

const EARLIER_JOB_PREVIEW_LIMIT = 10;

type FeedTabLabel = "今天" | "昨天" | "更早";

export default function CompanyFeedTimeline({ days }: { days: DayBucketPayload[] }) {
  const [activeTab, setActiveTab] = useState<FeedTabLabel>("今天");
  const [showAllEarlier, setShowAllEarlier] = useState(false);

  const daysByBucket = useMemo(() => {
    const grouped: Record<DayBucketPayload["bucket"], CompanyCardPayload[]> = {
      today: [],
      yesterday: [],
      earlier: [],
    };

    for (const day of days) {
      grouped[day.bucket].push(...day.companies);
    }

    return grouped;
  }, [days]);

  const activeBucket = FEED_TABS.find((tab) => tab.label === activeTab)?.bucket ?? "today";
  const activeCompanies = daysByBucket[activeBucket];
  const isEarlier = activeBucket === "earlier";
  const { companies: visibleCompanies, hasHiddenJobs } =
    isEarlier && !showAllEarlier ? limitCompaniesByJobs(activeCompanies, EARLIER_JOB_PREVIEW_LIMIT) : { companies: activeCompanies, hasHiddenJobs: false };

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
          <h2>这一栏暂时没有岗位</h2>
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
