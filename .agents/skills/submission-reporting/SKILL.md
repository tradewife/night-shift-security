---
name: submission-reporting
description: Human-grade bounty submission report assembly after a validated finding, including eligibility, deployed-binary proof, PoC packaging, screenshots, and caveats.
---

# Submission Reporting

Use this after a candidate has validator/fork reproduction and needs a human-readable Immunefi/Cantina report. The goal is to convert evidence into a submission that is clear, original, scoped, runnable, and honest about limitations.

## Non-negotiables

- Never claim more impact than measured.
- Never hide feasibility or configuration caveats.
- Never submit source-only evidence when the program requires deployed-contract impact.
- Never use audit/known-issue-adjacent language until you have checked the listed audits and known issues.
- Never include private keys, seed phrases, RPC secrets, auth tokens, or non-public customer data in the report, Gist, screenshots, or attachments.
- Never test on mainnet/public testnet unless the bounty explicitly allows it; prefer local validator/fork replay.

## Step 1: Eligibility alignment

Read the bounty page and record:

1. **Asset in scope**: exact program/contract/account.
2. **Impact in scope**: exact listed impact, not a paraphrase.
3. **PoC requirement**: runnable local/fork test required or optional.
4. **Deployed artifact requirement**: whether deployed code takes precedence over source.
5. **Known issues and audits**: listed known issues plus audit reports.
6. **Out-of-scope constraints**: privileged access, governance, oracle, liquidity, economic attacks, third-party systems, testing restrictions.
7. **KYC/payment constraints**: mention only if relevant for operator readiness.

If the evidence is configuration-dependent, label the finding as such. Example: "confirmed in deployed code; current live exploitability depends on enabling a fee-bearing Token-2022 redemption token."

## Step 2: False-positive controls

A submittable report should include at least one positive case and one negative control.

For Solana accounting bugs, prefer:

- Positive PoC on local `solana-test-validator`, `solana-program-test`, `anchor-bankrun`, or LiteSVM.
- Deployed-binary replay when rules require deployed-code proof:
  ```bash
  solana program dump -u <rpc> <program_id> /tmp/<program>.so
  solana-test-validator --reset --upgradeable-program <program_id> /tmp/<program>.so /tmp/upgrade-authority.json
  ```
- Negative controls showing the normal path succeeds.
- Exact balance deltas, not only "less than" assertions.
- Failure reason checks, not only `rejects.toThrow()`.
- Top-up/mitigation controls when liveness or insolvency is claimed.

Record controls in a concise machine-readable artifact such as `false_positive_checks.json`.

## Step 3: Report shape

Write the report in this structure.

### 1. Title

Use this formula:

`<vulnerability class> in <component/function> leads to <in-scope impact>`

Examples:

- `Token-2022 transfer-fee redemption accounting records gross deposits while vault receives net amount, causing stuck redemption requests`
- `Missing access control in updateConfig allows unprivileged fee manipulation`

### 2. Description

#### Brief / Intro

One short paragraph. State the bug and consequence without overclaiming.

#### Vulnerability Details

Explain:

- Vulnerable function(s)
- Trust boundary or missing check
- Relevant state writes
- Why the downstream path fails
- Why normal controls do not fail

Include small code snippets only where they clarify the root cause.

#### Impact Details

Map the finding to the exact bounty impact. Include:

- Measured balances before/after.
- Units and token decimals where relevant.
- Funds directly affected or a clear explanation why funds-at-risk is configuration-dependent.
- Whether the attack is unprivileged, user-triggered, admin-triggered, or governance/configuration-dependent.
- Whether this is theft, permanent freeze, insolvency, griefing, or only a best-practice issue.

#### References

Include:

- Program/contract address
- Source commit
- Relevant files/functions
- Audit/known-issue check result
- PoC gist link, if created

### 3. Proof of Concept

Give copy-paste commands and expected output. Include:

- Toolchain versions if the setup is fragile.
- Local validator/fork startup command.
- Test command.
- Expected JSON/balance deltas.
- Negative control command/output.
- Note that no mainnet/public testnet transactions were sent, if true.

## Step 4: Gist package

Create a **secret** Gist, not public. Include only sanitized files:

- `README.md`: concise summary, run commands, expected output, caveats.
- Main PoC test/script.
- False-positive controls.
- Summary JSON with measured deltas.

With GitHub CLI:

```bash
gh gist create --desc "<target> <bug class> PoC" README.md poc.spec.ts controls.spec.ts false_positive_checks.json
```

Notes:

- `gh gist create` defaults to secret unless `--public` is supplied.
- Scan staged files for secrets before creating the Gist.
- A Gist supports the report; it does not replace the written PoC section.

## Step 5: Screenshots

If the dashboard allows only one or two screenshots, choose:

1. Main PoC output showing exact measured deltas.
2. False-positive controls showing normal cases pass and the vulnerable case fails as expected.

Screenshots should show command, test name, output JSON, and pass status. If terminal color/log rendering makes the screenshot unreadable, use the underlying evidence file or Gist instead.

## Step 6: Humanized voice checklist

Before submission, rewrite to sound like an investigator, not a template:

- Use "I observed" for measured results.
- Use "appears" or "depends" for configuration caveats.
- Avoid buzzwords and exaggerated severity.
- Be explicit about what was not tested.
- Preserve uncertainty around current production exposure when the config check is negative.

Good caveat wording:

> I did not observe an active mainnet redemption offer with a fee-bearing Token-2022 `token_in` in my read-only config check. The issue is confirmed in the deployed program code, but current live exploitability appears configuration-dependent unless such an offer is or becomes enabled.

## Step 7: Final gate

Do not proceed to external posting until:

- JSON/evidence artifacts parse.
- PoC command reruns from a clean local environment.
- Negative controls pass.
- Deployed artifact replay is done when required.
- Full project validators pass or any unrelated failures are clearly documented.
- The report states the exact in-scope impact and any caveat.
- Human operator approves the final text and attachment set.

## Output artifacts

For each submission-ready finding, write or update:

- `data/security_results/bounty/submittable/<target>/<finding_id>.json`
- `data/security_results/investigations/<session>/false_positive_checks.json`
- `data/security_results/investigations/<session>/validation_summary.json`
- `data/security_results/lab_notebook/<session>.md`
- `SPEC.md` / `CHANGELOG.md` if project status changes
