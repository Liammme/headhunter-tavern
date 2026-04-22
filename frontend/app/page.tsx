import CompanyDaySection from "../components/CompanyDaySection";
import IntelligencePanel from "../components/IntelligencePanel";
import { fetchHomePayload } from "../lib/api";

export default async function HomePage() {
  const payload = await fetchHomePayload();
  const hasDays = payload.days.length > 0;
  const previewDay = payload.days[0];
  const previewCompanies = previewDay ? previewDay.companies.slice(0, 2) : [];

  return (
    <main className="page-shell">
      <section className="hero-shell" aria-labelledby="home-hero-title">
        <header className="home-hero-copy">
          <p className="eyebrow">情报封面</p>
          <h1 id="home-hero-title">先判断今天的猎场变化，再往下挑公司。</h1>
          <p>
            首屏先给你一张今天的情报封面，再把公司猎单池从底部露出来。用户第一眼应该先知道今天该盯什么，再进入行动。
          </p>
        </header>
        <IntelligencePanel
          intelligence={payload.intelligence}
          previewBucket={previewDay?.bucket ?? null}
          previewCompanies={previewCompanies}
        />
      </section>

      <section className="feed-shell" aria-labelledby="leaderboard-start-title">
        <header className="feed-shell-head">
          <p className="eyebrow">公司猎单池</p>
          <h2 id="leaderboard-start-title">从这里开始进入今天的公司档案卡。</h2>
        </header>
        {hasDays ? (
          payload.days.map((day) => (
            <CompanyDaySection key={day.bucket} bucket={day.bucket} companies={day.companies} />
          ))
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
