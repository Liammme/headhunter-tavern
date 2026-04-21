import CompanyDaySection from "../components/CompanyDaySection";
import IntelligencePanel from "../components/IntelligencePanel";
import { fetchHomePayload } from "../lib/api";

export default async function HomePage() {
  const payload = await fetchHomePayload();
  const hasDays = payload.days.length > 0;

  return (
    <main className="page-shell">
      <IntelligencePanel intelligence={payload.intelligence} />
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
    </main>
  );
}
