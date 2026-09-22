# Scenario C Phase 1 clean-fork feedback and proposed changes

This is upstream feedback produced by running the documentation from a real fork.

- **Upstream repository:** `rutgerpels/sreagent`
- **Test fork:** `PelsGit/sreagent`
- **Reviewed upstream commit:** `df8cd30`
- **Primary document:** `docs/scenario-c-private-gitops.md`
- **Audience assumed:** technical engineers and architects evaluating Azure SRE Agent

The fork was treated as an independent repository: GitHub Actions settings, OIDC federation, repository variables, secrets, runners, and GitHub App installation were not assumed to transfer from upstream.

## Phase 1 execution status

- **Step 1 — healthy baseline:** verified `infra/leak.auto.tfvars` on `main` contains `enable_slow_leak = false`.
- **Step 2 — private runner:** reused the already-provisioned resources in the dedicated resource group `rg-sreagent-scenario-c-runner`. Started the deallocated `Standard_D4s_v5` x64 VM and verified the repository runner `sreagent-scenario-c` is online and idle with exactly `self-hosted`, `Linux`, `X64`, `azure-private`, and `contosopay`. On the VM, Docker `29.1.3` and Azure CLI `2.90.0` are operational, and outbound HTTPS to GitHub and Azure Resource Manager succeeds.
- **Step 3 — Code Access choice:** GitHub App path selected, matching the intended Scenario C story.
- **Step 4 — GitHub App:** repository configuration contains a GitHub App client ID, key-name variable, enable flag, and PEM secret metadata. The App's live permissions and repository-only installation could not be independently read with the available GitHub user token; those settings remain a manual UI verification item before Phase 2.
- **Step 5 — variables and secret:** verified all nine App-path repository variables and the PEM secret name exist. Verified the OIDC deployment identity is a user-assigned managed identity in the dedicated runner resource group, with federation subject `repo:PelsGit/sreagent:ref:refs/heads/main`. It has Contributor and User Access Administrator at subscription scope. Verified the runner VNet is `10.50.0.0/16`, while the documented application default is `10.100.0.0/16`, so the default ranges do not overlap.
- Verified GitHub Actions is enabled, all five workflows are active, this is a fork of `rutgerpels/sreagent`, and no workflow has yet run in the fork.
- Verified `Microsoft.App` is registered and `Microsoft.App/agents` is available in Sweden Central.

No Scenario C application/state resources were deployed; Phase 2 was not started.

## Recommended upstream change set

I would split the correction into four reviewable commits while keeping them in one pull request.

### Commit 1 — make clean-fork bootstrap executable

**Files:** `docs/scenario-c-private-gitops.md`, `docs/deployment-reference.md`, plus a new runner-bootstrap reference or script.

1. Add a **clean-fork preflight** before the current healthy-baseline check:
   - confirm the fork is synchronized and `main` is the default branch;
   - enable Actions and verify all required workflows are active;
   - confirm the operator can manage Actions variables, secrets, and runners;
   - state explicitly that upstream secrets, variables, OIDC trust, runners, and App installations do not transfer to a fork.
2. Add an executable **OIDC bootstrap** for a user-assigned managed identity. Show the exact issuer, audience, and subject:

   ```text
   issuer:   https://token.actions.githubusercontent.com
   audience: api://AzureADTokenExchange
   subject:  repo:<fork-owner>/<repository>:ref:refs/heads/main
   ```

   Include commands to create the identity and federated credential, assign the tested Azure roles/scopes, set the three repository variables, and read everything back for verification. State that the production dispatch must run from the trusted `main` ref.
3. Replace “Owner or User Access Administrator” with separate requirements for:
   - the human bootstrap operator; and
   - the OIDC deployment identity.

   Use **Owner**, or **Contributor plus User Access Administrator**, at the scopes the workflow actually touches. Explicitly cover subscription-scoped role assignments and write access to the shared runner-network resource group.
4. Either provide a supported x64 runner bootstrap or change the prerequisite to “pre-provisioned.” A supported bootstrap should create a dedicated runner resource group, VNet, runner subnet, private-endpoint subnet, x64 VM, runner service, and the five fixed labels. Include start/stop and removal instructions.
5. Publish a tested package/preflight script and network destination reference for a restricted enterprise runner. Verify Docker daemon access as the runner service account, not just `docker --version`.

**Acceptance criteria:** a new fork with no inherited settings can follow the documented steps from zero to an online idle runner and a statically verified OIDC configuration without consulting the upstream author's environment.

### Commit 2 — fail early on invalid Scenario C inputs

**Files:** `.github/workflows/deploy.yml`, `.github/workflows/apply-infra.yml`, `infra/variables.tf` or Terraform `check` blocks.

1. Remove the `agentrg`, `agent-vnet`, and `private-endpoints` fallbacks for Scenario C. Fail validation with the exact missing repository-variable name.
2. Validate the application address plan as one unit:
   - every subnet is contained in `APP_VNET_ADDRESS_SPACE`;
   - the three application subnets do not overlap;
   - the application VNet does not overlap the runner VNet;
   - delegated/private-endpoint subnet sizes meet the documented minimums.
3. Replace the backend role-assignment `|| true` with explicit idempotency:
   - query for the assignment;
   - create it only when absent;
   - fail immediately with an authorization-specific message when creation fails.
4. Add a runner preflight step that reports missing executables, Docker socket access, DNS resolution, and required outbound endpoints before Terraform changes Azure.

**Acceptance criteria:** missing variables, bad CIDRs, missing tools, and missing Azure authorization fail in validation/preflight with an actionable error before state bootstrap or resource creation.

### Commit 3 — make shared private DNS reusable

**Files:** `.github/actions/discover-private-dns-zones/action.yml`, `.github/workflows/deploy.yml`, and the Scenario C networking inputs/docs.

Extend shared-zone discovery to `privatelink.blob.core.windows.net`, or add a required input for an existing Blob private DNS zone. Reuse an enterprise-managed zone/link rather than trying to attach the runner VNet to a second zone for the same namespace. Document subnet capacity, private-endpoint policy, DNS, peering, subscription, and resource-group permission assumptions.

**Acceptance criteria:** Scenario C can bootstrap state when the runner VNet is already linked to centrally managed Blob, ACR, and Key Vault private DNS zones in other resource groups.

### Commit 4 — correct security claims and deployment output

**Files:** `docs/scenario-c-private-gitops.md`, `README.md`, `.github/workflows/deploy.yml`, and any Scenario C talk-track text.

1. Replace the absolute “Reader-only / cannot mutate Azure because of RBAC” statement with the exact model:
   - workload access at the demo resource group is Reader;
   - both agent identities receive Monitoring Contributor at subscription scope for the incident lifecycle;
   - that built-in role has a residual monitoring write surface;
   - the reconciled tool policy is therefore a required guardrail, not merely defense in depth over a fully read-only identity.
2. Decide whether the subscription-wide Monitoring Contributor grant is genuinely required for both identities. If not, reduce it. If it is required, document and demonstrate the exception rather than presenting RBAC as absolute prevention.
3. Fix the deployment summary to say the GitHub App PEM is imported as a Key Vault **key**, not stored as a secret.
4. Change the Code Access statement to: without Code Access, the agent can investigate and describe a fix, but cannot create the remediation branch and pull request.
5. Add the persistent-runner threat-model note: repository-restricted runner group, trusted workflow changes, dedicated/ephemeral runner where possible, and best-effort—not guaranteed—PEM deletion.

**Acceptance criteria:** the documentation, Terraform grants, workflow summary, and on-stage security claims describe the same effective permissions and credential flow.

## Suggested test plan for the upstream PR

1. Create a new personal fork with no repository variables, secrets, runners, or App installation.
2. Follow only the updated documentation to bootstrap the runner and OIDC identity.
3. Confirm an omitted Scenario C network variable fails before Azure login/deployment work begins.
4. Confirm an invalid/overlapping address plan fails before resource creation.
5. Confirm a deployment identity without role-assignment authority gets an explicit authorization error at the assignment step.
6. Link the runner VNet to an existing Blob private DNS zone in a different resource group and verify state bootstrap reuses it.
7. Run Scenario C deployment from fork `main` and verify OIDC, private state, ACR, Key Vault, peering, and agent reconciliation.
8. Verify the deployment summary uses “Key Vault key” and accurately names the Monitoring Contributor exception.
9. Verify the GitHub App is installed only on the fork with Metadata Read, Contents Read/Write, and Pull requests Read/Write.
10. Tear down the deployed profile, then remove runner bootstrap resources and subscription-scope assignments using the documented cleanup path.

## Detailed findings and rationale

### 1. Critical: the documented Reader-only RBAC guarantee is inaccurate

**Runbook:** `docs/scenario-c-private-gitops.md:14-19`, `446-448`, `479-481`, `635-642`

The runbook repeatedly says Scenario C's agent holds Reader on Azure and that Azure RBAC prevents all Azure mutation. Terraform also grants both the agent's user-assigned and system-assigned identities **Monitoring Contributor at subscription scope** (`infra/agents.tf:192-208`). The built-in role includes write/delete/action permissions for alerts, action groups, metric alerts, workbooks, Monitor settings, Operational Insights resources, and deployments.

The global tool policy may still prevent the agent from invoking writes, and workload access at the demo resource group is Reader, but the stated two-layer guarantee is not literally true. The documentation and talk track should name the Monitoring Contributor exception and describe the exact residual write surface.

### 2. High: Phase 1 does not provision the runner it says it provisions

**Runbook:** `docs/scenario-c-private-gitops.md:59-60`, `102-121`

The prerequisite table says the runner is "Provisioned in phase 1," but Step 2 only tells the operator to register an already-available Linux x64 host. A clean-fork user gets no VM sizing/OS guidance, Azure network creation procedure, runner download/registration/service commands, runner-group configuration, or lifecycle/cleanup instructions.

Add either:

1. a complete reference implementation for a dedicated runner resource group, VNet, private-endpoint subnet, x64 VM, runner service, and labels; or
2. an explicit pre-provisioned-host prerequisite plus authoritative registration and network links.

The hard-coded `contosopay` runner label should also be called out as fixed and unrelated to the deployment prefix.

### 3. High: clean-fork OIDC bootstrap is not executable from the documentation

**Runbook/reference:** `docs/scenario-c-private-gitops.md:61`, `184-189`; `docs/deployment-reference.md:9-29`

The reference says to configure a federated credential but gives no identity-creation commands, issuer, audience, subject, scope assignments, or branch trust model. Federation for the upstream repository does not transfer to a fork. The production workflow does not use a GitHub Environment, so a `main` dispatch needs this exact subject:

```text
repo:<fork-owner>/<repository>:ref:refs/heads/main
```

Add an end-to-end Azure CLI or portal bootstrap, require dispatch from the trusted branch, and show read-back verification of the federated credential.

### 4. High: operator and deployment-identity permissions are underdocumented

**Runbook/reference:** `docs/scenario-c-private-gitops.md:56-64`; `docs/deployment-reference.md:25-29`

"Owner or User Access Administrator" is not a correct either/or prerequisite for creating the environment: User Access Administrator cannot create the resources. The deployment identity also needs resource creation plus role-assignment authority. The workflow creates resource groups, state storage, role assignments, private endpoints/private DNS, and Scenario C peering in both the application and shared runner VNet resource groups. Terraform also creates subscription-scoped Monitoring Contributor assignments.

Document operator and OIDC identity separately. A practical bootstrap is Owner, or Contributor plus User Access Administrator at the necessary scopes, with explicit shared-network permissions. If tighter custom roles are supported, publish the tested actions and scopes.

The workflow's `Storage Blob Data Contributor` assignment uses `|| true` (`.github/workflows/deploy.yml:295-301`), which hides missing authorization and later reports a misleading state-container failure. Preserve idempotency without suppressing real authorization errors.

### 5. High: runner package and egress prerequisites are incomplete

**Runbook:** `docs/scenario-c-private-gitops.md:110-118`

The workflow/scripts require more than Docker and Azure CLI: at least Bash, Git, jq, curl, `getent`, awk, sed, grep, cut, sha256sum, and best-effort file cleanup tools. Docker daemon access—not merely the CLI—must work for the runner service account.

The egress statement omits Entra login, GitHub Actions/tool downloads, Terraform releases/provider registries, Node downloads, npm, Docker Hub/base images, Azure data-plane/private endpoints, and SRE Agent APIs. Add a tested package preflight and an endpoint/FQDN reference for restricted enterprise networks.

### 6. High: shared runner-network requirements and Blob DNS behavior are underspecified

**Runbook:** `docs/scenario-c-private-gitops.md:59`, `115`, `187-199`, troubleshooting at `617-618`

The deployment assumes the runner VNet is in the target subscription, the deployment identity can modify its resource group, the private-endpoint subnet is undelegated and has capacity, private-endpoint policies are suitable, Azure private DNS resolution works from the runner, and bidirectional peering can be created.

The shared-zone discovery action handles ACR and Key Vault, but backend bootstrap creates/links `privatelink.blob.core.windows.net` in the runner-network resource group. A VNet already linked to an enterprise-managed Blob zone elsewhere can fail bootstrap. Add Blob-zone discovery/configuration equivalent to ACR/Key Vault, or clearly document the limitation and workaround.

### 7. Medium: required runner-network variables silently fall back to generic names

**Runbook/workflows:** `docs/scenario-c-private-gitops.md:177-190`; `.github/workflows/deploy.yml:202-223`; `.github/workflows/apply-infra.yml:163-183`

The docs call `RUNNER_NETWORK_RG`, `RUNNER_VNET_NAME`, and `RUNNER_PE_SUBNET_NAME` required, but workflows default missing values to `agentrg`, `agent-vnet`, and `private-endpoints`. A typo therefore becomes a confusing not-found failure—or targets an unintended shared network—instead of a validation error. Fail closed when any required Scenario C network variable is absent.

### 8. Medium: CIDR overrides need to be presented as one address plan

**Runbook:** `docs/scenario-c-private-gitops.md:191-199`

Changing only `APP_VNET_ADDRESS_SPACE` leaves three default subnet prefixes under `10.100.0.0/16`. Users generally need to set all four values together. Document containment, mutual non-overlap, minimum subnet sizes, non-overlap with the runner VNet, and provide one complete example. Add Terraform cross-variable validation or preflight checks so invalid combinations fail before Azure provisioning.

### 9. Medium: the generated deployment summary contradicts the runbook's key-based design

**Workflow:** `.github/workflows/deploy.yml:617-620`

The success summary says to store the PEM as a Key Vault **secret**, while the workflow and runbook correctly import it as a Key Vault **key**, and the runbook states secret URIs are rejected. Update the summary to the key-based flow. It also repeats the absolute Reader-only claim and should include the Monitoring Contributor exception.

### 10. Medium: clean-fork and GitHub App preflight is incomplete

**Runbook:** `docs/scenario-c-private-gitops.md:91-100`, `154-175`

Step 1 only checks the leak flag. Add checks that:

- the fork is synchronized and `main` is the default/workflow branch;
- Actions and the required workflows are enabled;
- the baseline value is committed, not merely changed locally;
- the operator can set Actions variables/secrets and manage runners;
- organization policy permits App creation/installation;
- the App is installed only on the intended fork with Metadata Read, Contents Read/Write, and Pull requests Read/Write.

### 11. Medium: persistent self-hosted runner and PEM controls need a threat-model note

**Runbook:** `docs/scenario-c-private-gitops.md:166-175`, `213-229`

The repository secret is materialized on a network-connected persistent runner. Recommend a repository-restricted runner group, trusted-maintainer/branch controls for workflow changes, and a dedicated or ephemeral runner where practical. Describe `shred` as best-effort deletion; it cannot guarantee physical erasure on SSD/COW-backed disks.

### 12. Low: Code Access wording overstates what is lost

**Runbook:** `docs/scenario-c-private-gitops.md:123-127`

Without Code Access, the agent can still investigate and describe/propose the fix in chat; it cannot create the remediation branch and pull request. Adjust the wording accordingly.

## Items requiring Phase 2 evidence

- Whether the existing GitHub App's live permissions and repository selection exactly match Step 4.
- Whether OIDC login succeeds from the fork's `main` workflow with the current managed identity.
- Whether `az ad sp show --id "$ARM_CLIENT_ID"` succeeds for the minimally authenticated deployment identity without extra Microsoft Graph directory permissions.
- Whether existing enterprise-managed Blob private DNS creates a conflict in a shared-network tenant.
