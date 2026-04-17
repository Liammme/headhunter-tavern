import CompanyDaySection from "../components/CompanyDaySection";
import IntelligencePanel from "../components/IntelligencePanel";
import { fetchHomePayload } from "../lib/api";

export default async function HomePage() {
  const payload = await fetchHomePayload();

  return (
    <main className="page-shell">
      <IntelligencePanel intelligence={payload.intelligence} />
      {payload.days.map((day) => (
        <CompanyDaySection key={day.bucket} bucket={day.bucket} companies={day.companies} />
      ))}
    </main>
  );
}
