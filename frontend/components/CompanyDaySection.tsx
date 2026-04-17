import CompanyCard from "./CompanyCard";
import type { CompanyCardPayload, DayBucketPayload } from "../lib/types";

export default function CompanyDaySection({
  bucket,
  companies,
}: {
  bucket: DayBucketPayload["bucket"];
  companies: CompanyCardPayload[];
}) {
  return (
    <section className="day-section">
      <h2 className="day-title">{renderBucketTitle(bucket)}</h2>
      <div className="company-list">
        {companies.map((company) => (
          <CompanyCard key={`${bucket}-${company.company}`} company={company} />
        ))}
      </div>
    </section>
  );
}

function renderBucketTitle(bucket: DayBucketPayload["bucket"]) {
  if (bucket === "today") {
    return "今天";
  }
  if (bucket === "yesterday") {
    return "昨天";
  }
  return "更早";
}
