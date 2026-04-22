"use client";

import React, { useEffect, useState } from "react";

import type { CompanyClueState } from "../lib/types";

const LOADING_MESSAGES = [
  "正在翻找公司档案",
  "正在整理重点岗位",
  "正在核对可用入口",
] as const;

type CompanyCluePanelProps = {
  clue: CompanyClueState;
};

export default function CompanyCluePanel({ clue }: CompanyCluePanelProps) {
  const [loadingIndex, setLoadingIndex] = useState(0);

  useEffect(() => {
    if (clue.status !== "loading") {
      setLoadingIndex(0);
      return;
    }

    const timer = window.setInterval(() => {
      setLoadingIndex((current) => (current + 1) % LOADING_MESSAGES.length);
    }, 900);

    return () => window.clearInterval(timer);
  }, [clue.status]);

  if (clue.status === "loading") {
    return (
      <section className="company-clue-panel company-clue-loading" aria-label="公司线索处理中" aria-live="polite">
        <div className="company-clue-panel-head">
          <p className="eyebrow">侦查线索</p>
          <h4>线索整理中</h4>
        </div>
        <div className="company-clue-loading-track" aria-hidden="true">
          {LOADING_MESSAGES.map((message, index) => (
            <div
              key={message}
              className={`company-clue-loading-item ${index === loadingIndex ? "is-active" : ""}`}
            >
              {message}
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (clue.status === "failure") {
    return (
      <section className="company-clue-panel company-clue-failure" aria-label="公司线索失败结果" aria-live="polite">
        <div className="company-clue-panel-head">
          <p className="eyebrow">侦查线索</p>
          <h4>线索生成失败</h4>
        </div>
        <p className="company-clue-narrative">{clue.narrative}</p>
        {clue.error_message ? <p className="company-clue-meta">异常原因：{clue.error_message}</p> : null}
      </section>
    );
  }

  return (
    <section className="company-clue-panel company-clue-success" aria-label="公司线索来信" aria-live="polite">
      <div className="company-clue-panel-head">
        <div>
          <p className="eyebrow">侦查线索</p>
          <h4>{clue.company} 线索来信</h4>
        </div>
        <p className="company-clue-meta">生成于 {formatGeneratedAt(clue.generated_at)}</p>
      </div>
      <p className="company-clue-narrative">{clue.narrative}</p>
      <div className="company-clue-sections">
        {clue.sections.map((section) => (
          <section key={section.key} className="company-clue-section">
            <h5>{section.title}</h5>
            <p>{section.content}</p>
          </section>
        ))}
      </div>
    </section>
  );
}

function formatGeneratedAt(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
