export type IntelligencePayload = {
  narrative: string;
  headline: string;
  summary: string;
  findings: string[];
  actions: string[];
};

export type JobCardPayload = {
  id: number;
  title: string;
  canonical_url: string;
  bounty_grade: "high" | "medium" | "low";
  tags: string[];
  claimed_names: string[];
};

export type CompanyCardPayload = {
  company: string;
  company_url?: string | null;
  company_grade: "focus" | "watch" | "normal";
  total_jobs: number;
  claimed_names: string[];
  jobs: JobCardPayload[];
};

export type DayBucketPayload = {
  bucket: "today" | "yesterday" | "earlier";
  companies: CompanyCardPayload[];
};

export type HomePayload = {
  intelligence: IntelligencePayload;
  days: DayBucketPayload[];
};
