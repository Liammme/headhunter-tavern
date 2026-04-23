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
  const signerName = company.claimed_by ?? company.claimed_names[0] ?? null;
  const estimatedBounty = renderEstimatedBounty(company);
  const isClaimed = Boolean(company.claim_status || company.claimed_names.length || company.claimed_by);

  return (
    <aside className="company-claim-seal" aria-label={isClaimed ? "公司签署状态位" : "公司认领状态位"}>
      {isClaimed ? (
        <>
          <div className="seal-mark" aria-hidden="true">
            <span>SEALED</span>
          </div>
          <dl className="seal-details">
            <div>
              <dt>Signature</dt>
              <dd className="seal-signature">{renderEnglishSignature(signerName)}</dd>
            </div>
            <div>
              <dt>预计赏金</dt>
              <dd>{estimatedBounty}</dd>
            </div>
          </dl>
        </>
      ) : (
        <div className="seal-unclaimed-row">
          <div className="seal-bounty">
            <span className="seal-bounty-label">预计赏金</span>
            <strong>{estimatedBounty}</strong>
          </div>
          {claimJob ? <ClaimDialog job={claimJob} onClaimCreated={onClaimCreated} /> : null}
        </div>
      )}
    </aside>
  );
}

function renderEstimatedBounty(company: CompanyClaimSealProps["company"]) {
  if (typeof company.estimated_bounty_amount === "number" && Number.isFinite(company.estimated_bounty_amount)) {
    return `¥${company.estimated_bounty_amount.toLocaleString("zh-CN")}`;
  }

  const bountyLabel = company.estimated_bounty_label?.trim();

  if (bountyLabel) {
    return bountyLabel;
  }

  return "待估算";
}

function renderEnglishSignature(signerName: string | null) {
  if (!signerName) {
    return "Signed";
  }

  return `Signed by ${signerName}`;
}
