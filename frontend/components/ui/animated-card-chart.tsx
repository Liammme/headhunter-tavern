"use client";

import * as React from "react";
import { useMemo, useState } from "react";

import { DEFAULT_CHART_COPY, type ChartCopy } from "../../lib/copy";

type CardProps = React.HTMLAttributes<HTMLDivElement>;

export type ChartDatum = {
  label: string;
  value: number;
};

export function AnimatedCard({ className, ...props }: CardProps) {
  return <div role="region" className={joinClassNames("animated-card-chart", className)} {...props} />;
}

export function CardBody({ className, ...props }: CardProps) {
  return <div role="group" className={joinClassNames("animated-card-body", className)} {...props} />;
}

type CardTitleProps = React.HTMLAttributes<HTMLHeadingElement>;

export function CardTitle({ className, ...props }: CardTitleProps) {
  return <h3 className={joinClassNames("animated-card-title", className)} {...props} />;
}

type CardDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;

export function CardDescription({ className, ...props }: CardDescriptionProps) {
  return <p className={joinClassNames("animated-card-description", className)} {...props} />;
}

export function CardVisual({ className, ...props }: CardProps) {
  return <div className={joinClassNames("animated-card-visual", className)} {...props} />;
}

type Visual3Props = {
  data: ChartDatum[];
  mainColor?: string;
  secondaryColor?: string;
  copy?: ChartCopy;
};

export function Visual3({ data, mainColor = "#75fb6e", secondaryColor = "#26a17b", copy = DEFAULT_CHART_COPY }: Visual3Props) {
  const [isActive, setIsActive] = useState(false);
  const chartBars = useMemo(() => buildChartBars(data, copy.fallbackLabels), [data, copy.fallbackLabels]);

  return (
    <div
      className={joinClassNames("animated-chart-visual", isActive && "is-active")}
      onMouseEnter={() => setIsActive(true)}
      onMouseLeave={() => setIsActive(false)}
      onFocus={() => setIsActive(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setIsActive(false);
        }
      }}
      style={
        {
          "--chart-main": mainColor,
          "--chart-secondary": secondaryColor,
        } as React.CSSProperties
      }
    >
      <div className="animated-chart-pills" aria-hidden="true">
        <span data-value="+15.2%">
          <i />
        </span>
        <span data-value="+18.7%">
          <i />
        </span>
      </div>
      <div className="animated-chart-tooltip" aria-hidden={!isActive}>
        <span>
          <i />
          {copy.tooltipTitle}
        </span>
        <p>{copy.tooltipDescription}</p>
      </div>
      <div className="animated-chart-grid" aria-hidden="true" />
      <div className="animated-chart-glow" aria-hidden="true" />
      <div className="animated-chart-bars" role="img" aria-label={copy.chartAriaLabel}>
        {chartBars.map((item, index) => {
          const height = isActive ? item.activeHeight : item.idleHeight;
          const isPositive = isActive || item.idleDirection === "positive";

          return (
            <button
              key={`${item.label}-${index}`}
              type="button"
              className="animated-chart-bar-button"
              aria-label={copy.barAriaLabel(item.label, item.value)}
            >
              <span
                className={joinClassNames(
                  "animated-chart-bar",
                  isPositive ? "is-positive" : "is-negative",
                )}
                style={{ height }}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}

function joinClassNames(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(" ");
}

function buildChartBars(data: ChartDatum[], fallbackLabels: [string, string, string]) {
  const source = data.length
    ? data
    : [
        { label: fallbackLabels[0], value: 0 },
        { label: fallbackLabels[1], value: 0 },
        { label: fallbackLabels[2], value: 0 },
      ];

  return REFERENCE_BARS.map((bar, index) => {
    const base = source[index % source.length];
    return {
      label: base.label,
      value: Math.max(0, base.value),
      ...bar,
    };
  });
}

const REFERENCE_BARS = [
  { idleHeight: 26, activeHeight: 36, idleDirection: "negative" },
  { idleHeight: 25, activeHeight: 54, idleDirection: "positive" },
  { idleHeight: 48, activeHeight: 92, idleDirection: "positive" },
  { idleHeight: 36, activeHeight: 74, idleDirection: "positive" },
  { idleHeight: 38, activeHeight: 36, idleDirection: "negative" },
  { idleHeight: 62, activeHeight: 56, idleDirection: "negative" },
  { idleHeight: 68, activeHeight: 56, idleDirection: "positive" },
  { idleHeight: 38, activeHeight: 38, idleDirection: "positive" },
  { idleHeight: 24, activeHeight: 74, idleDirection: "negative" },
  { idleHeight: 56, activeHeight: 92, idleDirection: "positive" },
  { idleHeight: 62, activeHeight: 54, idleDirection: "negative" },
  { idleHeight: 26, activeHeight: 92, idleDirection: "positive" },
] as const;
