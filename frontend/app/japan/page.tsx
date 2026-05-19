import CompanyFeedTimeline from "../../components/CompanyFeedTimeline";
import IntelligencePanel from "../../components/IntelligencePanel";
import { GridPattern } from "../../components/ui/grid-pattern";
import TrueFocus from "../../components/ui/true-focus";
import { Typewriter } from "../../components/ui/typewriter";
import { fetchJapanHomePayload } from "../../lib/api";

export default async function JapanPage() {
  const payload = await fetchJapanHomePayload();
  const hasDays = payload.days.length > 0;
  const reportDateLabel = formatReportDate(new Date());
  const dailyCaptureInfo = buildDailyCaptureInfo(payload.days);

  return (
    <main className="page-shell">
      <GridPattern
        width={38}
        height={38}
        x={-1}
        y={-1}
        strokeDasharray="4 3"
        squares={[
          [4, 2],
          [6, 5],
          [9, 3],
          [11, 8],
          [14, 4],
          [16, 10],
          [19, 6],
          [22, 12],
        ]}
        className="page-grid-pattern"
      />
      <section className="hero-shell" aria-labelledby="japan-hero-title">
        <header className="home-hero-copy">
          <div className="hero-brand-focus" aria-label="Talent Signal Japan">
            <TrueFocus
              sentence="Talent Signal Japan"
              blurAmount={4}
              borderColor="#6cff72"
              glowColor="rgba(108, 255, 114, 0.42)"
              animationDuration={0.75}
              pauseBetweenAnimations={1.2}
              className="hero-brand-focus-inner"
            />
          </div>
          <h1 id="japan-hero-title" aria-label="Japan market signals, isolated from global noise.">
            <Typewriter
              words={["Japan market signals, isolated from global noise."]}
              speed={58}
              delayBetweenWords={2600}
              cursor
              cursorChar="|"
            />
          </h1>
        </header>
        <IntelligencePanel
          intelligence={payload.intelligence}
          reportDateLabel={reportDateLabel}
          captureTitle={dailyCaptureInfo.title}
          captureDescription={dailyCaptureInfo.description}
          collectionStats={buildCollectionStats(payload.days)}
        />
      </section>

      <section className="feed-shell" aria-label="日本地区岗位列表">
        {hasDays ? (
          <CompanyFeedTimeline days={payload.days} showTrustRail={false} />
        ) : (
          <section className="empty-state" aria-live="polite">
            <p className="eyebrow">Japan Signal Status</p>
            <h2>最近还没有可展示的日本岗位</h2>
            <p>Japan 抓取任务完成前，这里会暂时保持空态。写入 Japan 数据后，将只展示日本地区独立数据源岗位。</p>
          </section>
        )}
      </section>
      <footer className="page-brand-footer" aria-label="Powered by Talentverse X">
        <a href="https://www.talent-verse.xyz/zh-hans/talentverse-x" target="_blank" rel="noopener noreferrer">
          <img src="/assets/talentverse-powered-by.svg" alt="Powered by Talentverse X" width={245} height={25} />
        </a>
      </footer>
    </main>
  );
}

function formatReportDate(date: Date) {
  const parts = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "numeric",
    day: "numeric",
  }).formatToParts(date);

  const year = parts.find((part) => part.type === "year")?.value ?? "";
  const month = parts.find((part) => part.type === "month")?.value ?? "";
  const day = parts.find((part) => part.type === "day")?.value ?? "";

  return `${year}/${month}/${day}`;
}

function buildDailyCaptureInfo(days: Awaited<ReturnType<typeof fetchJapanHomePayload>>["days"]) {
  const recent = days.find((day) => day.bucket === "within_3_days");
  const companies = recent?.companies ?? [];
  const jobCount = companies.reduce((sum, company) => sum + company.total_jobs, 0);
  const sourceNames = companies.map((company) => company.company).filter(Boolean);
  const sourceSummary = sourceNames.length ? sourceNames.slice(0, 6).join("、") : "暂无日本公司来源";
  const overflow = sourceNames.length > 6 ? `等 ${sourceNames.length} 家公司` : "";

  return {
    title: `近3天日本岗位 ${jobCount} 个 / 点击切换市场报告`,
    description: `分布来源：${sourceSummary}${overflow}。`,
  };
}

function buildCollectionStats(days: Awaited<ReturnType<typeof fetchJapanHomePayload>>["days"]) {
  const labels: Record<(typeof days)[number]["bucket"], string> = {
    within_3_days: "3天内",
    within_7_days: "7天内",
    earlier: "更早",
  };

  return days.map((day) => ({
    label: labels[day.bucket],
    value: day.companies.reduce((sum, company) => sum + company.total_jobs, 0),
  }));
}
