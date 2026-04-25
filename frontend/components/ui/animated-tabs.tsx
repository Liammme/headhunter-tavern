"use client";

import * as React from "react";
import { useEffect, useRef } from "react";
import { gsap } from "gsap";

export interface AnimatedTabsProps {
  tabs: { label: string }[];
  activeLabel: string;
  onChange: (label: string) => void;
  ariaLabel?: string;
  logoSrc?: string;
  logoAlt?: string;
}

export function AnimatedTabs({ tabs, activeLabel, onChange, ariaLabel, logoSrc, logoAlt = "筛选标志" }: AnimatedTabsProps) {
  const circleRefs = useRef<Array<HTMLSpanElement | null>>([]);
  const timelineRefs = useRef<Array<gsap.core.Timeline | null>>([]);
  const tweenRefs = useRef<Array<gsap.core.Tween | null>>([]);
  const logoImgRef = useRef<HTMLImageElement>(null);
  const logoTweenRef = useRef<gsap.core.Tween | null>(null);
  const tabsKey = tabs.map((tab) => tab.label).join("|");

  useEffect(() => {
    const layout = () => {
      circleRefs.current.forEach((circle, index) => {
        if (!circle?.parentElement) {
          return;
        }

        const pill = circle.parentElement;
        const { width, height } = pill.getBoundingClientRect();
        const radius = (width * width / 4 + height * height) / (2 * height);
        const diameter = Math.ceil(2 * radius) + 2;
        const delta = Math.ceil(radius - Math.sqrt(Math.max(0, radius * radius - width * width / 4))) + 1;
        const originY = diameter - delta;
        const label = pill.querySelector(".animated-tab-label");
        const hoverLabel = pill.querySelector(".animated-tab-label-hover");

        circle.style.width = `${diameter}px`;
        circle.style.height = `${diameter}px`;
        circle.style.bottom = `-${delta}px`;

        gsap.set(circle, {
          xPercent: -50,
          scale: 0,
          transformOrigin: `50% ${originY}px`,
        });

        if (label) {
          gsap.set(label, { y: 0 });
        }

        if (hoverLabel) {
          gsap.set(hoverLabel, { y: Math.ceil(height + 100), opacity: 0 });
        }

        timelineRefs.current[index]?.kill();
        const timeline = gsap.timeline({ paused: true });

        timeline.to(circle, { scale: 1.2, xPercent: -50, duration: 2, ease: "power3.easeOut", overwrite: "auto" }, 0);

        if (label) {
          timeline.to(label, { y: -(height + 8), duration: 2, ease: "power3.easeOut", overwrite: "auto" }, 0);
        }

        if (hoverLabel) {
          timeline.to(hoverLabel, { y: 0, opacity: 1, duration: 2, ease: "power3.easeOut", overwrite: "auto" }, 0);
        }

        timelineRefs.current[index] = timeline;
      });
    };

    layout();

    window.addEventListener("resize", layout);
    document.fonts?.ready.then(layout).catch(() => {});

    return () => {
      window.removeEventListener("resize", layout);
      timelineRefs.current.forEach((timeline) => timeline?.kill());
      tweenRefs.current.forEach((tween) => tween?.kill());
    };
  }, [tabsKey]);

  const handleMouseEnter = (index: number) => {
    const timeline = timelineRefs.current[index];
    if (!timeline) {
      return;
    }

    tweenRefs.current[index]?.kill();
    tweenRefs.current[index] = timeline.tweenTo(timeline.duration(), {
      duration: 0.3,
      ease: "power3.easeOut",
      overwrite: "auto",
    });
  };

  const handleMouseLeave = (index: number) => {
    const timeline = timelineRefs.current[index];
    if (!timeline) {
      return;
    }

    tweenRefs.current[index]?.kill();
    tweenRefs.current[index] = timeline.tweenTo(0, {
      duration: 0.2,
      ease: "power3.easeOut",
      overwrite: "auto",
    });
  };

  const handleLogoEnter = () => {
    const img = logoImgRef.current;
    if (!img) {
      return;
    }

    logoTweenRef.current?.kill();
    gsap.set(img, { rotate: 0 });
    logoTweenRef.current = gsap.to(img, {
      rotate: 360,
      duration: 0.25,
      ease: "power3.easeOut",
      overwrite: "auto",
    });
  };

  return (
    <div className="animated-tabs">
      {logoSrc ? (
        <span className="animated-tabs-logo" onMouseEnter={handleLogoEnter}>
          <img src={logoSrc} alt={logoAlt} ref={logoImgRef} />
        </span>
      ) : null}

      <div className="animated-tabs-track" role="tablist" aria-label={ariaLabel}>
        {tabs.map(({ label }, index) => {
          const isActive = activeLabel === label;

          return (
            <button
              key={label}
              type="button"
              role="tab"
              aria-selected={isActive}
              className={`animated-tab${isActive ? " animated-tab-active" : ""}`}
              onMouseEnter={() => handleMouseEnter(index)}
              onMouseLeave={() => handleMouseLeave(index)}
              onClick={() => onChange(label)}
            >
              <span
                className="animated-tab-hover-circle"
                aria-hidden="true"
                ref={(element) => {
                  circleRefs.current[index] = element;
                }}
              />
              <span className="animated-tab-label-stack">
                <span className="animated-tab-label">{label}</span>
                <span className="animated-tab-label-hover" aria-hidden="true">
                  {label}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
