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
          <p className="intel-preview">{intelligence.headline}</p>
        </div>
        <button type="button" onClick={() => setOpen((value) => !value)}>
          {open ? "收起" : "展开"}
        </button>
      </div>
      {open ? (
        <div className="intel-body">
          <p className="intel-narrative">{intelligence.narrative}</p>
          <p className="intel-footnote">基于近 14 天岗位池与历史轻量统计生成</p>
        </div>
      ) : null}
    </section>
  );
}
