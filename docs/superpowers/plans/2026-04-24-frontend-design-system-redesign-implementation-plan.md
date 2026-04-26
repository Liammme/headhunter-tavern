# Frontend Design System Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the frontend visual system into a bright, modular, Symbiosis-inspired intelligence console while preserving the existing company-first workflow.

**Architecture:** Keep the current Next.js App Router and React component boundaries. Make the first implementation pass primarily through `frontend/app/globals.css`, with small JSX class/label refinements only where CSS needs stable hooks or tests need explicit structure.

**Tech Stack:** Next.js 15, React 18, TypeScript, Vitest, Testing Library, CSS variables.

---

## File Map

- Modify `frontend/app/globals.css`: replace the detective tavern visual system with bright product tokens, grid background, surface classes, buttons, cards, dialogs, clue states, responsive rules.
- Modify `frontend/app/page.tsx`: keep data flow unchanged; add stable shell hooks if needed for the redesigned first screen and feed.
- Modify `frontend/components/IntelligencePanel.tsx`: preserve rendered information; adjust class structure to bright intelligence console sections.
- Modify `frontend/components/CompanyCard.tsx`: preserve behavior; add clearer class hooks for company header, action rail, evidence list.
- Modify `frontend/components/CompanyClaimSeal.tsx`: preserve claim behavior; revise copy/structure toward ownership module rather than seal metaphor.
- Modify `frontend/components/ClaimDialog.tsx`: preserve submit flow; align button and dialog class hooks.
- Modify `frontend/components/CompanyCluePanel.tsx`: preserve loading/failure/success states; align classes with status surface design.
- Modify tests under `frontend/components/*.test.tsx`: update assertions for the new design system vocabulary while keeping behavior assertions.
- Do not modify backend files.
- Do not add analytics, telemetry, network calls, or UI framework dependencies.

## Success Criteria

- `npm test` passes from `frontend`.
- `npm run build` passes from `frontend`.
- Desktop and mobile screenshots show a bright product console: white/near-white grid background, black text, gray surfaces, rounded cards, minimal shadows.
- Company remains the primary unit; jobs remain evidence.
- Claiming, clue loading, clue retry, expand earlier days, and expand jobs still work.

## Task 1: Baseline And Design-System Test Updates

**Files:**
- Modify: `frontend/components/IntelligencePanel.test.tsx`
- Modify: `frontend/components/CompanyCard.test.tsx`
- Modify: `frontend/components/CompanyFeedTimeline.test.tsx`

- [ ] **Step 1: Run current frontend tests**

```powershell
cd F:\赏金猎人\frontend
npm test
```

Expected: existing tests pass before production changes.

- [ ] **Step 2: Add failing assertions for the new intelligence console vocabulary**

In `frontend/components/IntelligencePanel.test.tsx`, update the first test to expect the redesigned section labels:

```tsx
expect(screen.getByText("猎场控制台")).toBeInTheDocument();
expect(screen.getByRole("heading", { level: 3, name: "今日机会雷达" })).toBeInTheDocument();
expect(screen.getByRole("complementary", { name: "今日行动信号" })).toBeInTheDocument();
```

Run:

```powershell
cd F:\赏金猎人\frontend
npm test -- IntelligencePanel.test.tsx
```

Expected: fail because current component still renders `猎场情报`, `今日招聘`, and `侧栏注记`.

- [ ] **Step 3: Add failing assertions for the new company ownership module**

In `frontend/components/CompanyCard.test.tsx`, update company claim expectations:

```tsx
expect(within(rightRail as HTMLElement).getByText("OWNER")).toBeInTheDocument();
expect(within(rightRail as HTMLElement).getByText("Signed by Ada")).toBeInTheDocument();
expect(within(rightRail as HTMLElement).queryByText("SEALED")).not.toBeInTheDocument();
```

Run:

```powershell
cd F:\赏金猎人\frontend
npm test -- CompanyCard.test.tsx
```

Expected: fail because current claim module still renders `SEALED`.

## Task 2: Intelligence Panel JSX Refinement

**Files:**
- Modify: `frontend/components/IntelligencePanel.tsx`
- Test: `frontend/components/IntelligencePanel.test.tsx`

- [ ] **Step 1: Rename user-facing section labels without changing data flow**

Change:

```tsx
<p className="eyebrow intel-paper-label">猎场情报</p>
```

to:

```tsx
<p className="eyebrow intel-paper-label">猎场控制台</p>
```

Change:

```tsx
<aside className="intel-notes" aria-label="侧栏注记">
```

to:

```tsx
<aside className="intel-notes" aria-label="今日行动信号">
```

Change:

```tsx
<h3>今日招聘</h3>
```

to:

```tsx
<h3>今日机会雷达</h3>
```

- [ ] **Step 2: Run intelligence panel tests**

```powershell
cd F:\赏金猎人\frontend
npm test -- IntelligencePanel.test.tsx
```

Expected: pass after matching test updates.

## Task 3: Company Claim Module JSX Refinement

**Files:**
- Modify: `frontend/components/CompanyClaimSeal.tsx`
- Test: `frontend/components/CompanyCard.test.tsx`

- [ ] **Step 1: Replace seal metaphor with ownership vocabulary**

Change claimed state visual marker from:

```tsx
<div className="seal-mark" aria-hidden="true">
  <span>SEALED</span>
</div>
```

to:

```tsx
<div className="seal-mark" aria-hidden="true">
  <span>OWNER</span>
</div>
```

Keep `renderEnglishSignature` and bounty rendering unchanged.

- [ ] **Step 2: Run company card tests**

```powershell
cd F:\赏金猎人\frontend
npm test -- CompanyCard.test.tsx
```

Expected: pass after matching test updates.

## Task 4: Global Design Tokens And Bright Product Shell

**Files:**
- Modify: `frontend/app/globals.css`
- Verify: visual screenshot and `npm test`

- [ ] **Step 1: Replace old tavern tokens with bright console tokens**

Use these token groups in `:root`:

```css
--background: #ffffff;
--foreground: #0a0a0a;
--muted: #667085;
--border: #eceef2;
--surface: #f8f8f8;
--surface-strong: #f3f4f6;
--accent: #75fb6e;
--accent-ink: #102a12;
--danger: #f6543e;
--success: #26a17b;
--radius-sm: 12px;
--radius-md: 16px;
--radius-lg: 24px;
--radius-xl: 32px;
--shadow-subtle: 0 4px 4px rgba(101, 104, 112, 0.03);
--shadow-lift: 0 18px 60px rgba(15, 23, 42, 0.08);
--page-width: 1168px;
```

- [ ] **Step 2: Replace body background**

Use white background with a light grid:

```css
body {
  min-width: 320px;
  color: var(--foreground);
  background:
    linear-gradient(rgba(17, 17, 17, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(17, 17, 17, 0.045) 1px, transparent 1px),
    var(--background);
  background-size: 64px 64px;
  font-family: var(--font-body-stack);
}
```

- [ ] **Step 3: Remove old decorative dependencies**

Remove or neutralize these old visual patterns:

- `clip-path` card cuts
- hard black offset shadows
- fixed tavern background image
- large rotations on cards
- old paper texture gradients

Expected: selectors can remain, but visual output should use rounded product surfaces.

- [ ] **Step 4: Run full frontend tests**

```powershell
cd F:\赏金猎人\frontend
npm test
```

Expected: pass. CSS-only changes should not break behavior tests.

## Task 5: Redesign Core Surfaces

**Files:**
- Modify: `frontend/app/globals.css`
- Verify: screenshot at desktop and mobile widths

- [ ] **Step 1: Redesign hero and intelligence surfaces**

Set:

- `.page-shell` max width to `var(--page-width)`.
- `.home-hero-copy h1` to black, modern, no text shadow.
- `.intel-paper` to white or near-white, `1px solid var(--border)`, `24px` radius, subtle shadow.
- `.intel-notes` and `.intel-note-card` to modular stats/action cards.
- `.intel-peek-shell` to a light product panel rather than dark tavern strip.

- [ ] **Step 2: Redesign company feed surfaces**

Set:

- `.day-section` as a clean section with no clipped paper edge.
- `.company-card` as `#fff` or `#f8f8f8`, `24px` radius, `1px solid var(--border)`.
- `.company-top` as two-column layout on desktop and one-column layout on mobile.
- `.company-claim-seal` as an ownership card with black icon marker and bounty number.
- `.job-row` as light evidence rows, not dark cards.

- [ ] **Step 3: Redesign controls**

Unify:

- `.claim-trigger`
- `.company-clue-tag`
- `.company-footer button`
- `.feed-more-button`
- `.text-button`
- `.company-clue-retry`

All controls should use stable radius, border, hover, active, focus, disabled states.

- [ ] **Step 4: Redesign dialogs and clue panels**

Set:

- `.claim-dialog` as a white floating panel with `24px` radius.
- `.company-clue-panel` as a status surface.
- `.company-clue-loading-item.is-active` as accent-highlighted progress row.
- `.company-clue-failure` as a subtle danger panel, not a saturated red block.

## Task 6: Responsive And Visual Verification

**Files:**
- No required source changes unless screenshots show layout issues.

- [ ] **Step 1: Build production frontend**

```powershell
cd F:\赏金猎人\frontend
npm run build
```

Expected: build succeeds.

- [ ] **Step 2: Start dev server**

```powershell
cd F:\赏金猎人\frontend
npm run dev
```

Expected: local Next server starts. Use the printed localhost URL.

- [ ] **Step 3: Capture desktop and mobile screenshots**

Use Edge headless against the local URL:

```powershell
& 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' --headless --disable-gpu --hide-scrollbars --window-size=1440,1400 --screenshot='F:\赏金猎人\frontend-redesign-desktop.png' 'http://localhost:3000'
& 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' --headless --disable-gpu --hide-scrollbars --window-size=390,1200 --screenshot='F:\赏金猎人\frontend-redesign-mobile.png' 'http://localhost:3000'
```

Expected:

- Desktop shows bright grid background and modular cards.
- Mobile stacks sections without horizontal overflow.
- Text does not overlap buttons or cards.

- [ ] **Step 4: Final status check**

```powershell
cd F:\赏金猎人
git status --short
```

Expected: only planned frontend files, tests, plan, and optional screenshot references are changed.

## Task 7: Commit

**Files:**
- Stage only files changed for this UI redesign.

- [ ] **Step 1: Commit implementation**

```powershell
cd F:\赏金猎人
git add docs/superpowers/plans/2026-04-24-frontend-design-system-redesign-implementation-plan.md frontend/app frontend/components
git commit -m "style: redesign frontend visual system"
```

Expected: one focused commit for the implemented redesign.
