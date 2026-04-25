import CompanyFeedTimeline from "../components/CompanyFeedTimeline";
import IntelligencePanel from "../components/IntelligencePanel";
import { GridPattern } from "../components/ui/grid-pattern";
import TrueFocus from "../components/ui/true-focus";
import { Typewriter } from "../components/ui/typewriter";
import { fetchHomePayload } from "../lib/api";

export default async function HomePage() {
  const payload = await fetchHomePayload();
  const hasDays = payload.days.length > 0;
  const reportDateLabel = formatReportDate(new Date());
  const dailyCaptureSummary = buildDailyCaptureSummary(payload.days);

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
      <section className="hero-shell" aria-labelledby="home-hero-title">
        <header className="home-hero-copy">
          <div className="hero-brand-focus" aria-label="Talent Signal">
            <TrueFocus
              sentence="Talent Signal"
              blurAmount={4}
              borderColor="#6cff72"
              glowColor="rgba(108, 255, 114, 0.42)"
              animationDuration={0.75}
              pauseBetweenAnimations={1.2}
              className="hero-brand-focus-inner"
            />
          </div>
          <h1 id="home-hero-title" aria-label="Signal over noise. Talent over hype.">
            <Typewriter
              words={["Signal over noise. Talent over hype."]}
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
          dailyCaptureSummary={dailyCaptureSummary}
          collectionStats={buildCollectionStats(payload.days)}
        />
      </section>

      <section className="feed-shell" aria-label="公司岗位列表">
        {hasDays ? (
          <CompanyFeedTimeline days={payload.days} />
        ) : (
          <section className="empty-state" aria-live="polite">
            <p className="eyebrow">赏金池状态</p>
            <h2>今天还没有可展示的岗位</h2>
            <p>
              抓取任务完成前，首页会暂时保持空态。等下一次抓取写入后，这里会自动展示按天聚合的公司机会池。
            </p>
          </section>
        )}
      </section>
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

function buildDailyCaptureSummary(days: Awaited<ReturnType<typeof fetchHomePayload>>["days"]) {
  const today = days.find((day) => day.bucket === "today");
  const companies = today?.companies ?? [];
  const jobCount = companies.reduce((sum, company) => sum + company.total_jobs, 0);
  const sourceNames = companies.map((company) => company.company).filter(Boolean);
  const sourceSummary = sourceNames.length ? sourceNames.slice(0, 6).join("、") : "暂无公司来源";
  const overflow = sourceNames.length > 6 ? `等 ${sourceNames.length} 家公司` : "";

  return `今日抓取 ${jobCount} 个岗位，分布来源：${sourceSummary}${overflow}。`;
}

function buildCollectionStats(days: Awaited<ReturnType<typeof fetchHomePayload>>["days"]) {
  const labels: Record<(typeof days)[number]["bucket"], string> = {
    today: "今天",
    yesterday: "昨天",
    earlier: "更早",
  };

  return days.map((day) => ({
    label: labels[day.bucket],
    value: day.companies.reduce((sum, company) => sum + company.total_jobs, 0),
  }));
}
