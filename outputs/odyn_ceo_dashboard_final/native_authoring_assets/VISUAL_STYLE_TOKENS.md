# Visual Style Tokens (Screenshot-Match)

Use these Tableau formatting defaults to match the provided references.

## Typography

- Title font: Tableau Book / Inter equivalent, 36 px, bold, dark navy
- Section title: 22 px, semibold
- Card title: 14–16 px, semibold
- KPI value: 44–52 px, bold
- Supporting text: 11–13 px

## Colors

- Primary text: `#111827`
- Secondary text: `#6B7280`
- Card border: `#E5E7EB`
- Dashboard background: `#F3F4F6`
- Card background: `#FFFFFF`

Status colors:

- MEASURED / healthy: `#16A34A`
- PARTIAL / caution: `#D97706`
- UNAVAILABLE / neutral: `#9CA3AF`
- Failure: `#DC2626`

Series colors:

- Utilization line: `#4F46E5`
- Reference line (50%): `#94A3B8` dashed
- Completed jobs: `#10B981`
- Failed jobs: `#EF4444`
- Stopped jobs: `#F59E0B`
- OOM bucket: `#B91C1C`

## Layout

- Outer dashboard padding: 20 px
- Card gap: 12–16 px
- Card corner radius (floating container workaround): 10–14 px visual effect
- Consistent card height in top row

## Tooltip contract

Every tooltip should include:

1. Metric definition in plain language
2. Unit and aggregation rule
3. Sample size / denominator
4. Freshness timestamp
5. Source note (measured vs unavailable)
