"use client";

import { useState } from "react";

import type { IntelligencePayload } from "../lib/types";

export default function IntelligencePanel({ intelligence }: { intelligence: IntelligencePayload }) {
  const [open, setOpen] = useState(false);

  return (
    <section className="intel-card">
      <div className="intel-head">
        <div>
          <p className="eyebrow">猎场情报</p>
          <h1>{intelligence.headline}</h1>
        </div>
        <button type="button" onClick={() => setOpen((value) => !value)}>
          {open ? "收起" : "展开"}
        </button>
      </div>
      {open ? (
        <div className="intel-body">
          <section className="intel-block">
            <h2>变化分析</h2>
            <p>{intelligence.summary}</p>
          </section>
          <div className="intel-columns">
            <section className="intel-block">
              <h2>重点发现</h2>
              <ul>
                {intelligence.findings.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
            <section className="intel-block">
              <h2>行动建议</h2>
              <ol>
                {intelligence.actions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            </section>
          </div>
          <p className="intel-footnote">基于近 14 天岗位池与历史轻量统计生成</p>
        </div>
      ) : null}
    </section>
  );
}
