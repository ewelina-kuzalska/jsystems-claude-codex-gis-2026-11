# Codex configuration examples

For Windows course setup, follow the [Polish participant steps](WINDOWS-QUICKSTART-PL.md). Merge settings into the actual user configuration at `$CODEX_HOME/config.toml`, or `~/.codex/config.toml` when CODEX_HOME is unset. Back up the existing file and preserve unrelated model/provider settings.

## User-wide Windows baseline

```toml
# Demonstration only: disables the local sandbox. Keep commented.
# sandbox_mode = "danger-full-access"
default_permissions = ":workspace"
approval_policy = "on-request"
approvals_reviewer = "auto_review"

[windows]
sandbox = "elevated"

[features]
prefer_mxc = false
network_proxy = false
```

The explicit `network_proxy = false` replaces any earlier enabled user setting. Merge entries into existing tables; do not create duplicate tables. Comment active legacy `sandbox_mode` and remove legacy `[sandbox_workspace_write]` when selecting named permission profiles. The built-in workspace default is suitable across projects. The selected legacy Windows backend is the measured course baseline; managed policy and explicit overrides can take precedence.

After active work is finished, run these from normal host PowerShell:

```powershell
codex app-server daemon restart
```

```powershell
codex app-server daemon version
```

```powershell
codex
```

Start a new chat for acceptance, then inspect the active permissions/MCP setup. A resumed chat can restore its saved permissions. Restart interrupts every session using that user's shared daemon. Use `update --from-cli` before restart only when deliberately aligning the daemon package to an updated installed CLI. `--no-daemon` is a separate diagnostic, not the course startup path.

## Reusable user examples and the course project

| File | Scope |
|---|---|
| [config.toml](config.toml) | Complete user example: normal :workspace default, six optional permission profiles, models and MCP examples. Merge only selected settings. |
| [permissions.toml](permissions.toml) | Minimal user permission/approval example with the same six profiles; :workspace default. |
| [rules/course.rules](rules/course.rules) | Reviewed command exceptions and denials. Copy to the user rules directory only if those rules should apply across projects. |
| [PERMISSIONS.md](PERMISSIONS.md) | Detailed profile/rule mapping and enforcement limits. |
| [examples/claude-command-parity.rules](examples/claude-command-parity.rules) | Inactive historical syntax comparison; do not install alongside the curated rules. |

The repository's active `.codex/config.toml` currently selects strict `course-root`. The optional `course-tools` profile is defined in these reusable examples; copying documentation does not activate it. The global baseline above sets `:workspace` for other projects. Global `prefer_mxc = false` also covers user-level server starts outside this repository; a project-only change does not update the user's baseline.

To use `course-tools` for a synthetic host-tool exercise, merge its definition and reviewed rules into the trusted project configuration and explicitly select it there. Check the effective settings in a new session. To make `course-tools` a user-wide default, merge its profile definition (the examples also contain strict alternatives) into the user config, set `default_permissions = "course-tools"`, and install reviewed `rules/course.rules` under `$CODEX_HOME/rules/`. A name alone does not install the profile. User rules apply across projects, and trusted project settings may select a different profile. Named permission profiles and model/provider `--profile` presets are different mechanisms.

`course-tools` enables command networking and has no OS-enforced .env/secrets deny-read rules. Use it for synthetic course data. Selected gh read operations and Playwright open/snapshot/close may run outside the sandbox through allow rules. The browser-open prefix permits arbitrary URLs. Other actions remain subject to sandbox/approval rules; prefix rules are not a complete firewall. Network domain restrictions require an active network proxy, which these examples do not enable.

Covered protected-branch push patterns, their matching gaps and the worktree prompt are described in [PERMISSIONS.md](PERMISSIONS.md#feature-branch-pushes-and-protected-branches); use server-side branch protection for enforcement.

Automatic review is independent of the permission profile: `on-request` + `auto_review` routes eligible approval requests to the reviewer. Allow-rule matches and ordinary sandboxed work do not require an extra review; forbidden rules still block. [Auto-review documentation](https://learn.chatgpt.com/docs/sandboxing/auto-review).

`course-workspace` is strict editing with secret-file denials; `course-root` is its compatibility alias. `course-review` is workspace read-only and `course-docs` allows docs/ writes; inherited temporary directories remain writable. `course-jetbrains` demonstrates a two-host network policy whose enforcement requires a proxy. Only one permission profile is selected at a time.

[Measured evidence and limitations](../../Research/codex-windows-sandbox-compatibility-2026-11-05.md). The examples target CLI 0.166.0; beta permission profiles and experimental rules may change.

## Separate course account

To use a training account next to a company one, see [separate-course-account](separate-course-account/README.md): a second `CODEX_HOME` with analysis and implementation profiles. On the course VM preserve the configured `CODEX_HOME` under `D:\AI\labuser`; the repository is `D:\jsystems-claude-codex-gis-2026-11`.

## Pytania i kontynuacja sesji

- [Formularze pytań, Plan i tymczasowy fragment AGENTS.md](../../Research/codex-interactive-questions-2026-11-05.md).
- [Jednorazowa kontynuacja po odnowieniu limitu](scheduled-continuation/README.md): dry-run domyślnie; dokładny UUID i jeden komunikat do kolejki. To nie jest automatyczna reaktywacja celu `/goal`.
