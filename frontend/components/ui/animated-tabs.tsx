"use client";

import * as React from "react";
import { useEffect, useRef } from "react";

export interface AnimatedTabsProps {
  tabs: { label: string }[];
  activeLabel: string;
  onChange: (label: string) => void;
  ariaLabel?: string;
}

export function AnimatedTabs({ tabs, activeLabel, onChange, ariaLabel }: AnimatedTabsProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const activeTabRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    const activeTabElement = activeTabRef.current;

    if (!container || !activeTabElement) {
      return;
    }

    const { offsetLeft, offsetWidth } = activeTabElement;
    const clipLeft = offsetLeft + 16;
    const clipRight = offsetLeft + offsetWidth + 16;

    container.style.clipPath = `inset(0 ${Number(100 - (clipRight / container.offsetWidth) * 100).toFixed()}% 0 ${Number(
      (clipLeft / container.offsetWidth) * 100,
    ).toFixed()}% round 17px)`;
  }, [activeLabel]);

  return (
    <div className="animated-tabs" role="tablist" aria-label={ariaLabel}>
      <div ref={containerRef} className="animated-tabs-active-layer" aria-hidden="true">
        <div className="animated-tabs-active-track">
          {tabs.map((tab) => (
            <button key={tab.label} type="button" className="animated-tab animated-tab-active" tabIndex={-1}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="animated-tabs-track">
        {tabs.map(({ label }) => {
          const isActive = activeLabel === label;

          return (
            <button
              key={label}
              ref={isActive ? activeTabRef : null}
              type="button"
              role="tab"
              aria-selected={isActive}
              className="animated-tab"
              onClick={() => onChange(label)}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
