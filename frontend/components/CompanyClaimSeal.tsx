"use client";

import React from "react";

import type { CompanyCardPayload } from "../lib/types";

type CompanyClaimSealProps = {
  company: Pick<
    CompanyCardPayload,
    "claimed_by" | "claim_status" | "claimed_names" | "jd_trust" | "jobs"
  >;
};

export default function CompanyClaimSeal({ company }: CompanyClaimSealProps) {
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
          <JdTrustRail jdTrust={company.jd_trust ?? null} />
        </>
      ) : (
        <div className="seal-unclaimed-row">
          <JdTrustRail jdTrust={company.jd_trust ?? null} />
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

function JdTrustRail({ jdTrust }: { jdTrust: CompanyCardPayload["jd_trust"] | null }) {
  if (!jdTrust) {
    return (
      <section className="jdtrust-rail jdtrust-rail-pending" aria-label="JD可信度甄别结果">
        <span className="jdtrust-rail-label">JD可信度待评估</span>
        <p>等待可信度层完成原帖证据和外部声誉核验。</p>
      </section>
    );
  }

  const checks = jdTrust.recommended_checks.slice(0, 2);
  const domainWarnings = (jdTrust.domain_warnings ?? []).slice(0, 3);

  return (
    <section className="jdtrust-rail" aria-label="JD可信度甄别结果">
      <div className="jdtrust-rail-head">
        <span className={`jdtrust-risk jdtrust-risk-${jdTrust.risk_level}`}>JD可信度：{renderJdTrustRisk(jdTrust.risk_level)}</span>
        {typeof jdTrust.trust_score === "number" ? <strong>{jdTrust.trust_score}</strong> : null}
      </div>
      {checks.length ? (
        <ul className="jdtrust-checks">
          {checks.map((check) => (
            <li key={check}>{check}</li>
          ))}
        </ul>
      ) : null}
      {domainWarnings.length ? (
        <div className="jdtrust-domain-warnings">
          <span>域名验证异常</span>
          <ul>
            {domainWarnings.map((warning) => (
              <li key={`${warning.fact_name}:${warning.fact_value}`}>{warning.label}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function renderJdTrustRisk(riskLevel: NonNullable<CompanyCardPayload["jd_trust"]>["risk_level"]) {
  if (riskLevel === "high") {
    return "高风险";
  }
  if (riskLevel === "needs_review") {
    return "需核验";
  }
  return "较可信";
}
