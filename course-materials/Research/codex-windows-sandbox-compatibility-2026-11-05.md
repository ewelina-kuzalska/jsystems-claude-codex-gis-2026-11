# Windows Codex sandbox compatibility: tested course profile

**Measured 2026-11-05 on the JSystems Windows VM, Codex CLI 0.166.0.** This note records one machine/session configuration. It is not a platform-wide guarantee. Keep it alongside the Polish participant checklist in [`WINDOWS-QUICKSTART-PL.md`](../agent-configs/codex/WINDOWS-QUICKSTART-PL.md).

## Latest course confirmation (6 November)

The measured procedure requires a managed daemon restart followed by a **new, non-resumed** session. Treat that as the course-tested procedure. The positive host-tool results below are not a negative sandbox-boundary test; perform the workspace-write/outside-write control from the quickstart before claiming isolation. No fresh native Windows run was performed during this document review.

## Recommendation

For a synthetic-data host-tool exercise, explicitly install and select the optional `course-tools` permission profile as described in the quickstart. The current project retains strict `course-root`; the examples alone do not change it. It extends Codex `:workspace`, retains `approval_policy = "on-request"` and `approvals_reviewer = "auto_review"`, and adds no filesystem deny-read entries. Set Windows sandbox preference explicitly to `elevated` and `features.prefer_mxc = false` for the tested baseline. Keep `course-workspace` and `course-root` as opt-in strict profiles; they retain exact and recursive deny rules for `.env`, `.env.local`, `.env.dev`, `.env.prod`, `.env.test`, and `secrets`. Never set danger-full-access or disable approvals as a workaround.

The profile's public network rules are unchanged from the existing strict course profiles (`enabled = true`, `"*" = "allow"`). Domain allowlisting is not enforced by a project-level proxy switch here. The host pilot covered `gh repo view` and the Playwright CLI open/snapshot/close lifecycle. Additional gh PR/issue read prefixes are policy-checked examples, not separately live-tested Windows results. These prefixes do not directly match `gh api`, PR mutations, `playwright-cli run-code`, shell wrappers or authentication changes. They do not validate trailing options: `open --config` can load additional configuration and `snapshot --filename` can write outside the workspace. They are not an option-level read-only policy. Existing forbidden rules for protected-branch pushes, force pushes, deletes and destructive operations remain. Rules are argv-prefix decisions, not a complete security boundary.

Context7 remote MCP is enabled without an API-key header. It is the preferred source for library/framework documentation: resolve a library ID, then query that ID. Playwright MCP remains disabled; the tested CLI is used for manual browser validation. Provider access is separate from command sandbox access.

## Evidence and interpretation

### Independent host PowerShell control

The user ran `windows_sandbox_probe.py` from a normal PowerShell session outside Codex. The report (sanitized synthetic host control) recorded a non-AppContainer, non-restricted interactive token, a readable synthetic file, successful `gh repo view`, Context7 resolving `/tailwindlabs/tailwindcss.com`, and successful Playwright `open`, `snapshot`, and `close` in separate foreground invocations. No real secret was read. A separate manual `about:blank` control had also succeeded.

### Actual Codex escalation control

The user ran the agent-exception trial from normal PowerShell with `--no-daemon` and temporary backend overrides. Its original Playwright commands placed the session option before the action, so the trial establishes approved escalation, not matching of the newly added allow prefixes. The later ordinary-session checks provide the separate positive observation. The sanitized escalation report records:

| Trial | Observed result |
|---|---|
| `elevated` with `course-root` (denied-read profile) | Codex returned `sandbox_setup_failed`; no child command completed. |
| `elevated` with temporary `course-cli-probe` extending `:workspace`, network enabled and no deny-read entries | All five separately invoked probes completed with exit code 0: host-token classification, synthetic-file read, `gh`, Context7 resolution, and Playwright open/snapshot/close. |

The report is sanitized: it does not contain account identifiers, token values, raw command output or real secrets. The diagnosis is bounded: removing denied reads for this host-tool profile was associated with successful actual escalation on this VM. It does **not** prove that every denied-read policy fails on every version, or that MXC is universally broken.

### Backend experiment limitations

The first probe run's backend matrix is not used as the basis for the default profile: some trials used an offline `:workspace` control or a temporary directory with ACL differences; failures therefore mixed network, filesystem and backend conditions. Native MXC was observed in an AppContainer/low-integrity context in that run, with Chrome IPC and GitHub authentication failures, but one matrix is insufficient to characterize MXC generally. Explicit fresh host escalation is the relevant positive control. Repeat the matrix only with matched profiles, paths, network conditions and a fresh Codex process.

## Reproduction and acceptance

Use the [Windows probe](../agent-configs/codex/diagnostics/windows_sandbox_probe.py) and its [unit tests](../agent-configs/codex/diagnostics/test_windows_sandbox_probe.py). Run the probe only from an interactive Windows PowerShell host, outside Codex and outside another container. It refuses to label an AppContainer/restricted/low-integrity parent as host. It creates an owned synthetic probe directory in the worktree; review and remove only that exact directory and report after preserving needed evidence.

For release acceptance, stop active work, restart the shared daemon and start a **new**, non-resumed ordinary Codex chat after explicitly installing the optional host-tool configuration from the quickstart and confirm: `/permissions` shows `course-tools`; `codex doctor --all` has no config errors; Context7's `resolve-library-id` and `query-docs` work from the native MCP client; the specific approved `gh` read commands and Playwright lifecycle work from Codex; writes stay inside the repository; protected-branch and destructive denials still match. A subprocess fixture does not prove MCP loading or the actual live provider. In particular, run a separate live smoke check with a real public repo and an owned Playwright session. Never paste or record keys, run `gh auth token`, or use customer data.

## Profile and tradeoffs

| Profile | Use | Consequence |
|---|---|---|
| `course-tools` (optional) | Course authoring and host-tool exercises on this Windows VM | Workspace-write and tested host escalation; no OS-enforced deny-read for environment/secrets paths. Keep such files out of the repo. |
| `course-workspace` / `course-root` | Demonstrating strict deny-read behavior | `.env*`/`secrets` denials remain; tested actual host escalation did not start under this profile. |
| `course-review`, `course-docs`, `course-jetbrains` | Existing narrow examples | Profile tables retained; proxy disabled in user examples, so domain restrictions require separate activation and validation. |

This trades OS-enforced denied reads in the optional host-tool profile for usable host integrations under the observed executor. `approval_policy = on-request`, narrow command rules, explicit human review, synthetic inputs and branch protection reduce risk but do not recreate filesystem deny-read guarantees. Do not use this profile on a workspace containing secrets. A separate Windows account/VM with no secrets is a reasonable course deployment boundary; follow the managed environment policy.

## Context7, GitHub CLI, Playwright and WezTerm

- The user-level `gh` login was available in the host control and the true Codex escalation trial, not in sandboxed trial processes. A 401 in a sandbox is not evidence that the Windows user has logged out.
- Context7's public remote MCP resolved the official Tailwind library ID from host and escalated probes. CLI probes alone do not certify the MCP server configured in the Codex process; acceptance must call both MCP tools.
- Playwright CLI and Chrome worked in the host control and escalated commands. In the tested VM the npm bin path was not inherited by the agent process, so prepend %APPDATA%\npm to PATH only in the PowerShell process that starts the fresh Codex session. Use separate foreground calls and an owned session ID. The CLI's child/daemon behavior inside a restrictive executor is a distinct lifecycle concern.
- `wezterm` was not found on `PATH` or standard installation paths during this check. No WezTerm run, Lua config test or stability comparison was performed. A terminal emulator selects a shell/window; Codex selects the sandbox separately. WezTerm cannot itself fix executor identity, Windows Credential Manager, browser IPC or sandbox settings. Keep it optional and describe ergonomic tradeoffs as hypotheses until measured.

## Configuration locations and lifecycle

The root `.codex/config.toml` is active when Codex trusts and opens this repository. The complete and minimal examples live in `course-materials/agent-configs/codex/`; both should keep their permissions profiles semantically aligned. User profiles in `$CODEX_HOME/config.toml` (under `D:\AI\labuser` on the course VM), managed policy, CLI flags and the app/server process can override project choices. Restart Codex after editing config, then inspect `/permissions` and startup diagnostics. `codex doctor` is not proof of an actual process token. Do not set `sandbox_mode` alongside named `default_permissions` without checking precedence. `network_proxy` is intentionally not activated in this repository because its daemon/firewall lifecycle was not part of this positive test.

## Official references

- [Windows sandbox modes](https://learn.chatgpt.com/docs/windows/windows-sandbox)
- [Permission profiles](https://learn.chatgpt.com/docs/permissions)
- [Codex configuration](https://learn.chatgpt.com/docs/config-file/config-basic)
- [Execpolicy rules](https://learn.chatgpt.com/docs/agent-configuration/rules)
- [Approval and security model](https://learn.chatgpt.com/docs/agent-approvals-security)
- [Context7 remote MCP](https://mcp.context7.com/mcp)


## Daemon lifecycle clarification and subsequent verification

The installed 0.166.0 CLI help confirms `codex app-server daemon restart`, `stop`, `start`, `version` and `update --from-cli`. Configuration rollout should restart the shared daemon after active work has stopped, then start a fresh ordinary `codex` chat. `--no-daemon` bypasses the shared server and is useful only as a separate diagnostic comparison; it does not validate the normal daemon path. Resuming a saved chat may restore its permission selection, so verify the active selection in the new chat.

The user subsequently reported a successful local session with `course-tools` selected, Context7 connected, resolve/query completed, authenticated read-only GitHub metadata returned, and separate Playwright open/snapshot/close calls successful. The preceding launch instructions included `--no-daemon`; ordinary daemon operation must be verified separately unless the user confirms they omitted that flag. These tool successes exercise allow-rule host exceptions and the separate MCP surface, not GitHub/Chrome running inside the sandbox.

In the existing assistant executor, subsequent default and explicitly escalated safe probes both remained AppContainer/low integrity; gh returned 401 and Chrome failed with Crashpad/pipe errors. This observation does not establish why a live permission change did not affect that executor, nor prove that low integrity alone caused the failures. Do not infer cache behavior, daemon state, or a separate runtime architecture solely from these results. The positive user-side local session and this unchanged executor are distinct observations.

Selected `allow` rules permit matching commands outside the sandbox. The ordinary permission profile still governs sandboxed commands. `network.enabled=true` enables outbound command networking; without an active proxy the domain table does not constrain direct destinations. `course-tools` has no secret-file deny-read rules. Check these boundaries before selecting the profile on a synthetic-data VM.


## Normal daemon confirmation and approval reviewer

After a full restart, the user explicitly confirmed that an ordinary `codex` session was connected to the active daemon and worked with the custom course profile. This supersedes the earlier uncertainty about whether the successful user-side session used `--no-daemon`.

The optional course-tools setup combines its profile, `approval_policy = "on-request"` and `approvals_reviewer = "auto_review"`. The configuration acceptance check now protects that combination. Official documentation defines it as automatic review for eligible approval requests with a custom permission boundary; the menu's profile label alone does not establish the reviewer setting. It is not a guarantee that a separate running chat has no UI/session override.

Post-restart probes from the existing assistant executor still returned AppContainer/low-integrity metadata. A read-only gh call returned 401; Git push --dry-run failed in Credential Manager/MSYS startup; Playwright about:blank failed in Chrome IPC/Crashpad startup; querying the running daemon version was denied by Windows. No remote branch or PR was changed by these probes. The active assistant execution policy explicitly routes escalations to auto_review, but approval did not remove that observed process containment. This remains an unresolved executor-specific behavior, not evidence that the user's ordinary daemon session or stored GitHub login failed.


## Global user configuration correction

The owning user config was subsequently inspected for sandbox/approval selectors only. It still had active sandbox_mode=danger-full-access and features.prefer_mxc=true, while the tested worktree had the new project settings and the original application checkout retained its older project profile. This configuration mismatch must be considered before attributing behavior to a daemon defect.

At the user's explicit request, the global config was backed up and updated atomically: danger-full-access remains as a commented demonstration, default_permissions=:workspace, approval_policy=on-request, approvals_reviewer=auto_review, windows.sandbox=elevated, prefer_mxc=false. Parsed comparison confirmed no unrelated settings changed. This verifies the file update; it does not claim that the already-running server/executor reloaded it.

Reusable full/minimal user examples now default to :workspace and include opt-in course-tools definitions. The current project retains course-root until explicitly changed for an exercise. Documentation explains user-wide profile installation and command-rule scope. Restart the daemon after active work has finished and validate a fresh normal session; no daemon restart was performed by the assistant during this change.
