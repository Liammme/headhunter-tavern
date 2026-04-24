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

export type CompanyClueRequest = {
  company: string;
};

export type CompanyClueStatus = "loading" | "success" | "failure";

export type CompanyClueSection = {
  key: string;
  title: string;
  content: string;
};

export type CompanyClueResponse = {
  status: CompanyClueStatus;
  company: string;
  generated_at: string;
  narrative: string;
  sections: CompanyClueSection[];
  error_message?: string | null;
};

export type CompanyClueState =
  | {
      status: "loading";
      company: string;
      generated_at: string;
      narrative: string;
      sections: CompanyClueSection[];
      error_message?: null;
    }
  | {
      status: "success" | "failure";
      company: string;
      generated_at: string;
      narrative: string;
      sections: CompanyClueSection[];
      error_message?: string | null;
    };
