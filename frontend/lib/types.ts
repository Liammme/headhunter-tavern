export type IntelligencePayload = {
  narrative: string;
  headline: string;
  summary: string;
  findings: string[];
  actions: string[];
  living_report?: LivingReportPayload | null;
};

export type LivingReportPayload = {
  kind: "living_market_report";
  schema_version: "living-market-report-v1";
  headline: string;
  version: number;
  mode: "baseline_seed" | "incremental_update";
  previous_snapshot_id: number | null;
  seed_window_days: number;
  generated_at: string;
  executive_summary: string;
  sections: LivingReportSection[];
  claims: LivingReportClaim[];
  watchlist: LivingReportWatchItem[];
  data_quality: LivingReportDataQuality;
};

export type LivingReportSection = {
  section_id: string;
  title: string;
  body: string;
  claim_ids: string[];
};

export type LivingReportClaim = {
  claim_id: string;
  previous_claim_id: string | null;
  status: "new" | "reinforced" | "weakened" | "retired";
  claim: string;
  confidence: "low" | "medium" | "high";
  evidence_ids: string[];
  evidence_notes: string[];
  change_reason: string;
};

export type LivingReportWatchItem = {
  topic: string;
  why_watch: string;
  evidence_ids: string[];
};

export type LivingReportDataQuality = {
  baseline_note?: string;
  posted_at_fact_count?: number;
  collected_at_fallback_count?: number;
  unknown_company_count?: number;
  sample_count?: number;
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
};

export type DayBucketPayload = {
  bucket: "within_3_days" | "within_7_days" | "earlier";
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
