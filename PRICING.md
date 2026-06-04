# ELD Build Pricing (internal notes)

Pricing lives on the public proposal page (Section 9) in a two-scenario structure. This file holds the rate basis and history, not the published numbers (those live on the page).

## Rate basis (2026-06-04, revised same day)

- Senior engineer: $6,500 per week (x2)
- QA engineer: $2,000 per week
- Adam: $6,500 per week while on the project (was $4,000 in the first draft). Presented on the page as a third senior engineer, not by name; the rate matches the senior rate exactly so the framing is clean.
- Core team weekly (2 senior + 1 QA): $15,000
- Accelerated team weekly (3 senior + 1 QA): $21,500
- No buffer or Phase 2 redistribution in this model; phases price as rate x weeks. Phase 2 stays a $5,000 loss-leader (3 weeks of Adam).
- One week added to Core Build in both scenarios versus the first draft (8 to 9 base).

## Published scenarios

### Scenario A · Core team · 19 weeks · $245,000

| Phase | Duration | Team | Fixed Price |
|---|---|---|---|
| 1. Research and Assessment | Complete | Adam | $0 |
| 2. ProposalType and Scope Lock | 3 weeks | Adam | $5,000 |
| 3. Core Build | 9 weeks | 2 senior eng + 1 QA | $135,000 |
| 4. Log Module and Data Transfer | 3 weeks | 2 senior eng + 1 QA | $45,000 |
| 5. Pilot, Certification Support, and Handoff | 4 weeks | 2 senior eng + 1 QA | $60,000 |
| **Total** | **19 wks** | | **$245,000** |

### Scenario B · Accelerated build · 16 weeks · $265,000

Build phases compressed roughly 20% (16 build weeks to 13: 7.5 / 2.5 / 3, half-week rounding). Presented as a third senior engineer on Phases 3 and 4, rolling off for Phase 5 (pilot and handoff run on the core team; the phase stays at 3 weeks since it is mostly calendar-driven). Internally the third senior is Adam at the matching $6,500 rate. The sell: three weeks sooner to pilot and certification-ready, for $20,000 more (about 8%).

| Phase | Duration | Team | Fixed Price |
|---|---|---|---|
| 1. Research and Assessment | Complete | Adam | $0 |
| 2. ProposalType and Scope Lock | 3 weeks | Adam | $5,000 |
| 3. Core Build | 7.5 weeks | 3 senior eng + 1 QA | $161,250 |
| 4. Log Module and Data Transfer | 2.5 weeks | 3 senior eng + 1 QA | $53,750 |
| 5. Pilot, Certification Support, and Handoff | 3 weeks | 2 senior eng + 1 QA | $45,000 |
| **Total** | **16 wks** | | **$265,000** |

## History

- 2026-06-04 (fifth revision): Scenario B reframed on the page as "Accelerated build" with a third senior engineer, no longer naming Adam or describing the role as part-time. Numbers unchanged.
- 2026-06-04 (fourth revision): Adam rolled off Phase 5 in Scenario B. B: 16 wks / $265,000.
- 2026-06-04 (third revision): +1 week to Core Build in both scenarios, Adam's part-time rate to $6,500. A: 19 wks / $245,000. B: 16 wks / $284,500.
- 2026-06-04 (second revision): pricing restored to the page. A: 18 wks / $230,000 (2 senior at $6,500, QA at $2,000). B: 15 wks / $233,000 (Adam part-time at $4,000).
- 2026-06-04 (first, post-call): certification moved to Tenna (FMCSA compliance expert), DVIR de-scoped, portal narrowed to log management. 18 weeks, $259,250, built on $16,950 per team-week (2 senior at $6,000 + QA at $2,500, +10% buffer, +$1,000/wk Phase 2 redistribution). Unpublished price.
- Pre-call model: 23 weeks, $344,000 (phases: $5,000 / $135,600 / $67,800 / $67,800 / $67,800).

## Outside the estimate (unpriced on the page and here)

Ongoing compliance and maintenance, the FMCSA compliance expert (Tenna-side hire), cloud infrastructure pass-through ($4,000 to $8,000 per month at Tenna's likely scale), backend platform operations, mobile telemetry tooling, production support, and existing-customer migration.
