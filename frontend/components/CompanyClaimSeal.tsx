"use client";

import React from "react";

import ClaimDialog from "./ClaimDialog";
import type { CompanyCardPayload } from "../lib/types";

type CompanyClaimSealProps = {
  company: Pick<
    CompanyCardPayload,
    "claimed_by" | "claim_status" | "claimed_names" | "jobs"
  >;
  claimJob: CompanyCardPayload["jobs"][number] | null;
  onClaimCreated?: (claimerName: string) => void;
};

export default function CompanyClaimSeal({ company, claimJob, onClaimCreated }: CompanyClaimSealProps) {
  const signerName = company.claimed_by ?? company.claimed_names[0] ?? null;
  const isClaimed = Boolean(company.claim_status || company.claimed_names.length || company.claimed_by);

  return (
    <aside className="company-claim-seal" aria-label={isClaimed ? "公司签署状态位" : "公司认领状态位"}>
      {isClaimed ? (
        <>
          <div className="seal-mark" aria-hidden="true">
            <span>OWNER</span>
          </div>
          <dl className="seal-details">
            <div>
              <dt>Signature</dt>
              <dd className="seal-signature">{renderEnglishSignature(signerName)}</dd>
            </div>
          </dl>
        </>
      ) : (
        <div className="seal-unclaimed-row">
          {claimJob ? <ClaimDialog job={claimJob} onClaimCreated={onClaimCreated} /> : null}
        </div>
      )}
    </aside>
  );
}

function renderEnglishSignature(signerName: string | null) {
  if (!signerName) {
    return "Signed";
  }

  return `Signed by ${signerName}`;
}
