# ELD Build Pricing (internal notes)

Pricing restored to the public proposal page on 2026-06-04 with updated rates and a two-scenario structure. This file now holds the rate basis and history, not the published numbers (those live on the page).

## Rate basis (2026-06-04)

- Senior engineer: $6,500 per week (was $6,000)
- QA engineer: $2,000 per week (was $2,500)
- Adam, part-time: $4,000 per week
- Core team weekly (2 senior + 1 QA): $15,000
- Accelerated team weekly (core + Adam part-time): $19,000
- No buffer or Phase 2 redistribution in this model; phases price as rate x weeks. Phase 2 stays a $5,000 loss-leader (3 weeks of Adam).

## Published scenarios

### Scenario A · Core team · 18 weeks · $230,000

| Phase | Duration | Team | Fixed Price |
|---|---|---|---|
| 1. Research and Assessment | Complete | Adam | $0 |
| 2. ProposalType and Scope Lock | 3 weeks | Adam | $5,000 |
| 3. Core Build | 8 weeks | 2 senior eng + 1 QA | $120,000 |
| 4. Log Module and Data Transfer | 3 weeks | 2 senior eng + 1 QA | $45,000 |
| 5. Pilot, Certification Support, and Handoff | 4 weeks | 2 senior eng + 1 QA | $60,000 |
| **Total** | **18 wks** | | **$230,000** |

### Scenario B · Core team + Adam part-time · 15 weeks · $233,000

Build phases compressed 20% (15 build weeks to 12). Per-phase durations rounded to half-weeks for the published table (6.5 / 2.5 / 3 instead of 6.4 / 2.4 / 3.2); the totals are exact.

| Phase | Duration | Team | Fixed Price |
|---|---|---|---|
| 1. Research and Assessment | Complete | Adam | $0 |
| 2. ProposalType and Scope Lock | 3 weeks | Adam | $5,000 |
| 3. Core Build | 6.5 weeks | 2 senior eng + 1 QA + Adam (pt) | $123,500 |
| 4. Log Module and Data Transfer | 2.5 weeks | 2 senior eng + 1 QA + Adam (pt) | $47,500 |
| 5. Pilot, Certification Support, and Handoff | 3 weeks | 2 senior eng + 1 QA + Adam (pt) | $57,000 |
| **Total** | **15 wks** | | **$233,000** |

The sell: Scenario B lands 3 weeks sooner for $3,000 more (about 1%).

## History

- 2026-06-04 (later): pricing restored to the page at the new rates above, two scenarios.
- 2026-06-04 (earlier): post-call rework after the June 4 session with Jose. Certification moved to Tenna (FMCSA compliance expert), DVIR de-scoped, portal narrowed to log management. That model: 18 weeks, $259,250, built on $16,950 per team-week (2 senior at $6,000 + QA at $2,500, +10% buffer, +$1,000/wk Phase 2 redistribution).
- Pre-call model: 23 weeks, $344,000 (phases: $5,000 / $135,600 / $67,800 / $67,800 / $67,800).

## Outside the estimate (unpriced on the page and here)

Ongoing compliance and maintenance, the FMCSA compliance expert (Tenna-side hire), cloud infrastructure pass-through ($4,000 to $8,000 per month at Tenna's likely scale), backend platform operations, mobile telemetry tooling, production support, and existing-customer migration.
