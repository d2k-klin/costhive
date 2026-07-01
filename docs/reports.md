# Reports

CostHive writes a consolidated, money-first report in up to four formats. All
generation is **local** — no data leaves your machine.

## Formats

| Format | File | Use |
|--------|------|-----|
| HTML | `report.html` | Self-contained, branded, interactive (filter by category/tool/confidence/risk). The client deliverable. |
| Markdown | `report.md` | Diff-friendly, pasteable into tickets/emails. |
| JSON | `findings.json` | Machine-readable — pipe into your own tooling. |
| PDF | `report.pdf` | Printable deliverable (opt-in). |

Choose with `--format html,md,json,pdf` (default `html,md,json`). `--pdf` is a
shorthand that adds PDF.

A rendered example: [../examples/sample-report.html](../examples/sample-report.html)
· [../examples/sample-report.md](../examples/sample-report.md).

## What's in the report

1. **Headline** — total estimated monthly (and annual) savings, plus the
   **safe-vs-judgment-call split**.
2. **Savings by category** — where the money is (see [categories.md](categories.md)).
3. **Savings by risk** — how safe it is to act.
4. **Quick wins** — high-value, low-risk, defensible opportunities to do first.
5. **Top opportunities** — ranked by dollar impact.
6. **Tools** — status, findings, savings, and version of each tool (evidence).
7. **All opportunities** — every finding with resource, `$`/mo, confidence, risk,
   and recommended action.

## Branding (consultant reports)

```bash
costhive scan --role-arn <role-arn> --external-id secret \
  --client-name "Acme Corp" --logo ./acme-logo.png --pdf
```

- `--client-name` sets the report header and PDF cover.
- `--logo` embeds an image (base64, so the HTML stays self-contained).
- The report includes a scan-metadata block (account, identity, timestamp, CostHive
  + tool versions) for evidence integrity.

## Interpreting savings

- Numbers are **estimates from public list prices**, provided to rank opportunities.
- Every finding carries **confidence** and **risk** — see [categories.md](categories.md).
- The headline separates **safe savings** (reversible) from **judgment-call**
  savings (may affect a workload). Present the safe number as bankable; the rest as
  worth investigating.

## PDF rendering

PDF reuses the HTML as the single source of truth via its `@media print` rules.

- **WeasyPrint** (default, pure-Python) — needs system libs pango/cairo (bundled in
  Docker; `pip install "costhive[pdf]"` for source installs).
- **Chromium** (`--pdf-engine chromium`) — pixel-perfect if you have Chrome/Chromium.

A PDF failure never aborts the other formats.

## Multi-account output

Each account gets its own report directory; a **roll-up** across all accounts is
written at the top level. See [usage.md](usage.md#scan-multiple-accounts).
