"use client";

import * as React from "react";
import { useMemo, useState } from "react";

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
};

export function Visual3({ data, mainColor = "#75fb6e", secondaryColor = "#26a17b" }: Visual3Props) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const chartBars = useMemo(() => buildChartBars(data), [data]);
  const maxAbsValue = useMemo(() => Math.max(...chartBars.map((item) => Math.abs(item.value)), 1), [chartBars]);

  return (
    <div
      className="animated-chart-visual"
      style={
        {
          "--chart-main": mainColor,
          "--chart-secondary": secondaryColor,
        } as React.CSSProperties
      }
    >
      <div className="animated-chart-pills" aria-hidden="true">
        <span>
          <i />
          +15.2%
        </span>
        <span>
          <i />
          +18.7%
        </span>
      </div>
      <div className="animated-chart-grid" aria-hidden="true" />
      <div className="animated-chart-glow" aria-hidden="true" />
      <div className="animated-chart-bars" role="img" aria-label="每日岗位收集数量统计图">
        {chartBars.map((item, index) => {
          const height = Math.max(16, Math.round((Math.abs(item.value) / maxAbsValue) * 70));
          const isHovered = hoveredIndex === index;
          const isPositive = item.value >= 0;

          return (
            <button
              key={`${item.label}-${index}`}
              type="button"
              className="animated-chart-bar-button"
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
              onFocus={() => setHoveredIndex(index)}
              onBlur={() => setHoveredIndex(null)}
              aria-label={`${item.label}，${Math.abs(item.value)} 个岗位`}
            >
              <span
                className={joinClassNames(
                  "animated-chart-bar",
                  isPositive ? "is-positive" : "is-negative",
                  isHovered && "is-hovered",
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

function buildChartBars(data: ChartDatum[]) {
  const source = data.length
    ? data
    : [
        { label: "今天", value: 0 },
        { label: "昨天", value: 0 },
        { label: "更早", value: 0 },
      ];

  const expanded = Array.from({ length: 14 }, (_, index) => {
    const base = source[index % source.length];
    const direction = index % 5 === 0 || index % 7 === 0 ? -1 : 1;
    const offset = (index % 4) * 2;
    return {
      label: base.label,
      value: direction * Math.max(1, base.value + offset),
    };
  });

  return expanded;
}
