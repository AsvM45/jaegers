# Security and private data handling

JAEGERS is an educational research repository, not an enterprise production service. Security reports still warrant private triage.

**Do not post vulnerabilities that reveal a live secret in public Issues, PRs, Discussions, Actions logs, Copilot sessions, or Wiki pages.** For a potential vulnerability, use GitHub's **private vulnerability reporting** feature if enabled under the repository **Security** tab. If unavailable, contact the repository maintainers privately using a trusted channel. Do not assume a public issue is private.

## Protected information

- Datathon organizer tokens, signed agreements, private receipts, registration metadata, hidden outcomes/targets and other teams' submissions.
- Local `research_runs/`, frozen CSV+ZIP bytes, unpublished datasets and any artifact that may contain private identifiers or competition secrets.
- Databricks/cloud credentials, access tokens, GitHub App keys, OAuth secrets, billing, local file locations or personally identifiable data.
- AI agent chat excerpts, private connector results and attached documents unless their owners explicitly authorize public publication.

Use trusted/least-privilege token scopes, no tokens in PR-head Actions code, and do not permit untrusted PR contents to run under privileged `pull_request_target` without a carefully reviewed design. The always-on gate uses a read-only repository token for metadata. Separate external cloud execution requires explicit account-level permission.

## Reporting scope and response

A responsible report should include affected repository path/commit, minimal reproduction, observed impact, and safe remediation proposal. Maintainers will assess and coordinate an appropriate fix; there is no guaranteed SLA or formal bug bounty. Do not disclose known credentials in a proof-of-concept.

If a secret is accidentally exposed, treat it as compromised: revoke/rotate it through its owner, inspect affected cloud/GitHub actions and access logs, remove public copies where feasible, and document the incident without reposting the secret. Deleting a git commit does **not** by itself erase data from all clones or prior Git history.

## Research integrity

Security and scientific integrity overlap: no future-tick features, no public test-answer inference, no unknown query labels and no misleading official-score claims. Compliance witnesses reporting `NOT_CERTIFIED` must not be advertised as organizer approvals. See [science provenance](docs/science/EVALUATION_AND_PROVENANCE.md) and [release status](docs/CURRENT_STATE.md).
