"use client";

import React from "react";

import ClaimDialog from "./ClaimDialog";
import type { CompanyCardPayload } from "../lib/types";

type CompanyClaimSealProps = {
  company: Pick<
    CompanyCardPayload,
    "claimed_by" | "claim_status" | "claimed_names" | "estimated_bounty_amount" | "estimated_bounty_label" | "jobs"
  >;
  claimJob: CompanyCardPayload["jobs"][number] | null;
  onClaimCreated?: (claimerName: string) => void;
};

export default function CompanyClaimSeal({ company, claimJob, onClaimCreated }: CompanyClaimSealProps) {
  const signerName = company.claimed_by ?? company.claimed_names[0] ?? "待签署";
  const claimStatus = renderClaimStatus(company.claim_status, company.claimed_names);
  const estimatedBounty = renderEstimatedBounty(company);

  return (
    <aside className="company-claim-seal" aria-label="公司签署区">
      <p className="eyebrow">签署区</p>
      <p className="seal-status">{claimStatus}</p>
      <dl className="seal-details">
        <div>
          <dt>公司线索认领</dt>
          <dd>{signerName}</dd>
        </div>
        <div>
          <dt>预计赏金</dt>
          <dd>{estimatedBounty}</dd>
        </div>
      </dl>
      {claimJob ? <ClaimDialog job={claimJob} onClaimCreated={onClaimCreated} /> : null}
    </aside>
  );
}

function renderClaimStatus(
  claimStatus: CompanyCardPayload["claim_status"],
  claimedNames: CompanyCardPayload["claimed_names"],
) {
  if (claimStatus) {
    return claimStatus;
  }

  if (claimedNames.length) {
    return "已签署";
  }

  return "待签署";
}

function renderEstimatedBounty(company: CompanyClaimSealProps["company"]) {
  if (company.estimated_bounty_amount) {
    return `¥${company.estimated_bounty_amount.toLocaleString("zh-CN")}`;
  }

  if (company.estimated_bounty_label) {
    return company.estimated_bounty_label;
  }

  return "待估算";
}
