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
  claimed_by?: string | null;
  claim_status?: string | null;
  estimated_bounty_amount?: number | null;
  estimated_bounty_label?: string | null;
};

export type DayBucketPayload = {
  bucket: "today" | "yesterday" | "earlier";
  companies: CompanyCardPayload[];
};

export type HomePayload = {
  intelligence: IntelligencePayload;
  days: DayBucketPayload[];
};
