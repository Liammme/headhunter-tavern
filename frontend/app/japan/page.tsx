import JapanFeedContent from "../../components/JapanFeedContent";
import JapanHomeContent from "../../components/JapanHomeContent";
import { GridPattern } from "../../components/ui/grid-pattern";
import TrueFocus from "../../components/ui/true-focus";
import { Typewriter } from "../../components/ui/typewriter";
import { fetchJapanHomePayload } from "../../lib/api";

export default async function JapanPage() {
  const payload = await fetchJapanHomePayload();
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
          <h1 id="japan-hero-title" aria-label="日本の採用シグナルを、ひと目で。">
            <Typewriter
              words={["日本の採用シグナルを、ひと目で。"]}
              speed={58}
              delayBetweenWords={2600}
              cursor
              cursorChar="|"
            />
          </h1>
        </header>
        <JapanHomeContent
          intelligence={payload.intelligence}
          reportDateLabel={reportDateLabel}
          captureTitle={dailyCaptureInfo.title}
          captureDescription={dailyCaptureInfo.description}
          collectionStats={buildCollectionStats(payload.days)}
        />
      </section>
      <JapanFeedContent days={payload.days} />
      <footer className="page-brand-footer" aria-label="Powered by Talentverse X">
        <a href="https://www.talent-verse.xyz/zh-hans/talentverse-x" target="_blank" rel="noopener noreferrer">
          <img src="/assets/talentverse-powered-by.svg" alt="Powered by Talentverse X" width={245} height={25} />
        </a>
      </footer>
    </main>
  );
}

function formatReportDate(date: Date) {
  const parts = new Intl.DateTimeFormat("ja-JP", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "numeric",
    day: "numeric",
  }).formatToParts(date);

  const year = parts.find((part) => part.type === "year")?.value ?? "";
  const month = parts.find((part) => part.type === "month")?.value ?? "";
  const day = parts.find((part) => part.type === "day")?.value ?? "";

  return `${year}.${month}.${day}`;
}

function buildDailyCaptureInfo(days: Awaited<ReturnType<typeof fetchJapanHomePayload>>["days"]) {
  const recent = days.find((day) => day.bucket === "within_3_days");
  const companies = recent?.companies ?? [];
  const jobCount = companies.reduce((sum, company) => sum + company.total_jobs, 0);
  const sourceNames = companies.map((company) => company.company).filter(Boolean);
  const sourceSummary = sourceNames.length ? sourceNames.slice(0, 6).join("、") : "取得元なし";
  const overflow = sourceNames.length > 6 ? ` ほか ${sourceNames.length}社` : "";

  return {
    title: `直近3日 ${jobCount}件 / マーケットレポートを開く`,
    description: `取得元：${sourceSummary}${overflow}。`,
  };
}

function buildCollectionStats(days: Awaited<ReturnType<typeof fetchJapanHomePayload>>["days"]) {
  const labels: Record<(typeof days)[number]["bucket"], string> = {
    within_3_days: "3日以内",
    within_7_days: "7日以内",
    earlier: "それ以前",
  };

  return days.map((day) => ({
    label: labels[day.bucket],
    value: day.companies.reduce((sum, company) => sum + company.total_jobs, 0),
  }));
}
