> **Later course measurement (2026-11-05, Codex CLI 0.166.0):** this October report is historical and does not describe the newly measured course VM configuration. A fresh host PowerShell and actual Codex escalation trial passed with a temporary workspace profile without deny-read; the strict profile failed at sandbox setup. See the [dated compatibility report](codex-windows-sandbox-compatibility-2026-11-05.md) and [Polish participant steps](../agent-configs/codex/WINDOWS-QUICKSTART-PL.md). This evidence does not establish universal MXC instability.

# Codex CLI on Windows: daemon updates, sandbox loops and ignored escalations

*Field report, 15-16 October 2026. Codex CLI 0.162.1 (standalone installer) with the app-server daemon, Windows 11 25H2, using an account without local admin rights. The original field investigation used local session files (`~/.codex/sessions/**/rollout-*.jsonl`), the log database (`~/.codex/logs_2.sqlite`), the sandbox log (`~/.codex/.sandbox/sandbox.<date>.log`) and the openai/codex source and issue tracker.*

Use this when Codex on Windows shows repeated UAC prompts, says "token invalid" for tools that work in your own terminal, or keeps failing commands although it "asked for escalation".

## 1. Architecture you need to know

Since about 0.160, the Codex CLI is a **client**. Agents run in a separate **app-server daemon**, and each command runs in its own sandboxed process:

```
codex (TUI client) --unix socket--> codex app-server --managed-daemon --> per-command sandbox helpers
                                    codex app-server daemon pid-update-loop (auto-updater)
```

- The CLI and the daemon are **versioned separately**. `codex app-server daemon version` prints both (`cliVersion`, `appServerVersion`).
- State lives in `CODEX_HOME` (`~/.codex`): `packages/app-server-daemon/` (daemon releases), `app-server-daemon/` (pid files), `app-server-control/app-server-control.sock`.

## 2. Updating the daemon after a CLI update

```powershell
codex app-server daemon update --from-cli --yes
```

```powershell
codex app-server daemon version
```

**Problem seen:** `Error: timed out waiting for daemon installer lock ...\packages/app-server-daemon\install.lock`.

**Cause (from source, `codex-rs/app-server-daemon/src/install_lock.rs`):** on Windows the lock file is opened exclusively (`share_mode(0)`), polled every 50 ms, and abandoned after 30 s. A long-running `codex app-server daemon pid-update-loop` process from the old version kept the handle open. `daemon stop` stops the server but **not** that updater process.

**Fix:**

```powershell
codex app-server daemon stop
```

```powershell
Get-CimInstance Win32_Process -Filter "Name='codex.exe'" | Select-Object ProcessId, CommandLine
```

```powershell
Stop-Process -Id ([int](Read-Host 'PID of the confirmed pid-update-loop process only'))
```

```powershell
codex app-server daemon update --from-cli --yes
```

```powershell
codex app-server daemon start
```

```powershell
codex app-server daemon version
```

`--from-cli` pins the daemon to your CLI build and switches off the auto-updater.

## 3. Windows sandbox backends in 0.162

| Backend | How it isolates | Notes |
|---|---|---|
| `elevated` | Runs commands as separate local users `CodexSandboxOffline` / `CodexSandboxOnline`, with firewall (WFP) rules and ACLs | Setup needs UAC (`codex-windows-sandbox-setup.exe`). Sandbox users have **no access to your Credential Manager or interactive desktop**. |
| `unelevated` | Restricted token | **Cannot enforce deny-read rules.** With a profile that denies `.env*`/`secrets`, Codex refuses to start: `windows unelevated restricted-token sandbox cannot enforce deny-read restrictions directly; refusing to run unsandboxed`. |
| MXC (`[features] prefer_mxc = true` or `[windows] sandbox = "mxc"`) | Microsoft Execution Containers (AppContainer-style), no admin setup | Needs Windows 11 24H2 26100.9278+ or 25H2 26200.9278+. Works on a Windows 365 Cloud PC. Deny-read was verified to work. Open problems: `EPERM realpath` on the profile root (breaks `pnpm dlx`/Node tooling), no cursor/desktop control (`SetCursorPos` -> error 5, issue #53650), path issues (#53786, #53765). |

`[windows] sandbox` selects a backend; it has no "off" value. Removing it does not imply a fixed fallback: legacy feature flags, managed requirements and MXC preference affect selection. The original machine fell back to `unelevated`; a clean 0.162.1 install may resolve to no Windows backend. Check `codex doctor` for the effective `sandbox backend` rather than assuming.

Validate the selected backend in an isolated test checkout containing only synthetic fixtures. For a deny-read probe, create a dummy `.env` containing `DUMMY=not-a-secret` in that throwaway checkout, select the profile being tested, and confirm that `codex sandbox --permission-profile <your-profile> -- cmd.exe /d /c type .env` denies access. Never point the probe at an existing credential file. Native Windows backend enforcement was observed in the original investigation and has not been rerun on every workshop machine.

## 4. Symptom: 7-15 UAC prompts for codex-windows-sandbox-setup.exe

**Cause:** the sandbox log shows the stored firewall configuration flipping between two values:

```
sandbox setup required: offline firewall settings changed (stored_ports=[], desired_ports=[3128, 8084])
sandbox setup required: offline firewall settings changed (stored_ports=[3128, 8084], desired_ports=[])
```

- The project `.codex/config.toml` enabled `[features] network_proxy = true`, so project threads want proxy ports `[3128, 8084]`.
- Daemon background threads (working directory `~/.codex`) do not load the project config, so they want `[]`.
- Every flip triggers a full elevated setup, which means one UAC prompt. Subagents and resumed sessions make it worse because each thread checks on its own.
- Parallel setups collide. That produces `orchestrator_helper_incomplete: setup helper exited successfully before setup completed` and `failed to grant ... ACE on user profile ... used by another process (os error 32)`.

You can confirm it by decoding the base64 argument shown in the UAC dialog ("Show more details"). It is the setup payload, including `proxy_ports` and `command_cwd`.

**Fix:** keep `network_proxy` consistent across all layers. Either remove it from the project config or enable it in the user config. A one-time prompt after a Codex upgrade (setup marker version change) is expected.

## 5. Symptom: tools work in your terminal but not in Codex (`gh`, desktop, screenshots)

- `gh` stores its token in Windows Credential Manager under **your** account. Inside any Codex sandbox (`elevated` sandbox user, or MXC container) the token is not visible, so `gh auth status` reports "The token in default is invalid" and `gh pr list` returns HTTP 401.
- GUI QA is blocked the same way. Under `elevated`, `Graphics.CopyFromScreen` fails with "The handle is invalid" and Java tests that need a desktop fail. Under MXC, `SetCursorPos` fails with error 5 and the token reports `TokenIsAppContainer = 1`.

For a profile without denied reads, the intended path is escalation: the model sends `"sandbox_permissions":"require_escalated"`, the reviewer (`approvals_reviewer = "auto_review"` or you) approves, and the command can run outside the sandbox. An exec-policy rule can pre-approve it, subject to the caveat below:

```
# ~/.codex/rules/default.rules
prefix_rule(pattern=["gh", "auth", "status"], decision="allow")
prefix_rule(pattern=["gh", ["pr", "issue", "run", "repo"], ["view", "list", "diff", "checks", "status"]], decision="allow")
```

**Denied-read caveat (0.162.1):** profiles containing deny-read entries, including the course profiles, retain filesystem enforcement even for approved or `allow`-matched commands. Codex rejects escalation when a suitable sandbox is unavailable. Approval and command rules therefore cannot restore Credential Manager or interactive desktop access for these profiles. See [command rules and approval](../agent-configs/codex/PERMISSIONS.md#command-rules-and-approval). Preserve the denied-read boundaries and report the missing runtime prerequisite instead of loosening the profile.

Check a rule with `codex execpolicy check --rules ~/.codex/rules/default.rules -- gh pr view 1`. When several rules match, **the most restrictive decision wins**, so a catch-all `prompt` rule for `gh` overrides narrower `allow` rules.

## 6. Escalation and resumed-session failures reported in 0.162.1

The original field investigation reported escalation requests that remained sandboxed and a resumed thread retaining old deny entries after a permission change. These are observations from that build, not a guarantee about other versions. Public reports: [ignored escalation and resumed-thread permissions #54440](https://github.com/openai/codex/issues/54440), [repeated sandbox setup from proxy-port changes #54441](https://github.com/openai/codex/issues/54441).

Check whether the command actually ran under the intended identity and whether an approval event occurred; the model asking for escalation is not evidence that it happened. Review sanitized logs locally without publishing credentials, session contents or private identifiers.

After an authorized permission configuration change, start a new session and transfer a short non-secret task summary. A resumed thread may retain its old policy. If the backend still fails, record the exact version, command, identity and error, then report the missing prerequisite. Keep denied-read boundaries and approvals intact; disabling the sandbox is not a troubleshooting fix. Approval policy and sandbox policy are separate controls, and neither a command allow rule nor automatic review guarantees that an OS identity can access the interactive desktop or credential store.

## 7. FAQ

**Is this caused by Entra ID or the Windows 365 VM?** Not for the main problems. The UAC loop comes from inconsistent `network_proxy` configuration, and the ignored escalation is Codex logic; neither depends on the account type. MXC was tested and works on the Cloud PC. Entra ID does show up elsewhere (user SIDs `S-1-12-1-...`; see issue #43354 about setup-marker ACLs on domain accounts), and a non-admin account makes every elevated setup a visible UAC prompt. Those make the symptoms more visible, but they are not the root cause.

**Why might another machine behave differently?** The reported combination was: Windows-native Codex with the daemon pinned to 0.162.1, a custom permission profile with deny-read rules, `network_proxy` enabled only at project level, auto-review approvals, and resumed sessions using subagents, the interactive desktop and `gh`. A default setup (no project-level proxy flag, no GUI QA, or Codex in WSL/macOS) avoids most of it.

**It worked before. What changed?** The CLI/daemon update from 0.160.0 to 0.162.1. It changed the sandbox setup marker, which forced re-provisioning, and in this setup escalation stopped reaching the reviewer.

**Will WSL work better?** For CLI work, most likely yes. The Linux sandbox is a different implementation (Landlock/bubblewrap): no sandbox Windows users, no UAC, no MXC, no Credential Manager. `gh` in WSL has its own login (`~/.config/gh`). The Codex desktop app can also run its agent in WSL. Limits:
- Whether the ignored-escalation bug also affects Linux was **not verified**.
- QA of a **Windows** Swing desktop app has to happen on Windows. WSLg runs the Linux JVM, which is a different runtime and look-and-feel.

## 8. Checklist

1. `codex app-server daemon version`: versions match?
2. `codex doctor`: sandbox backend, startup warnings, MCP paths. A WSL path such as `/mnt/c/...` in a Windows-native config cannot be resolved.
3. Repeated UAC prompts: grep `sandbox setup required` in `~/.codex/.sandbox/sandbox.<date>.log`.
4. "Token invalid" or desktop errors: run the same command in `codex sandbox ...`. If it fails only there, it is the sandbox identity. Then check whether escalation actually happened (section 6).
5. Report upstream with the CLI Bug template and a sanitized `codex doctor --json` result. Share private session identifiers only through an appropriate support channel.

## Sources

- openai/codex source: `codex-rs/app-server-daemon/src/install_lock.rs`, `codex-rs/prompts/templates/permissions/approval_policy/on_request_rule_request_permission.md`
- Public investigation reports: [#54440](https://github.com/openai/codex/issues/54440) (escalation and resumed-thread permissions), [#54441](https://github.com/openai/codex/issues/54441) (UAC loop from proxy_ports changes)
- Issues: #53650 (Computer Use under MXC 0x80070005), #53786, #53765, #50915 (MXC), #40217, #30445, #43354 (sandbox setup marker / ACL)
- Codex config docs: "Windows sandbox mode" (`prefer_mxc`), learn.chatgpt.com/docs/config-file/config-basic
