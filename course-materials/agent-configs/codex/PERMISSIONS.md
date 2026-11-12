> **User vs project setup:** merge the [user baseline and optional course profiles](README.md) into the actual CODEX_HOME config. Reusable examples default to :workspace; the current project selects strict course-root; course-tools is an optional profile in the reusable examples. To select course-tools globally, install its definition and reviewed user-scope rules, then change the user default. See the [Polish steps](WINDOWS-QUICKSTART-PL.md).

> **Windows evidence, Codex CLI 0.166.0, 5-6.11.2026:** a host-escalation trial succeeded with a temporary workspace-write profile without denied reads, while a strict course-root trial failed during sandbox setup. This is machine-specific evidence. The optional course-tools profile demonstrates that tradeoff; .env and secrets are not OS-denied in it. Keep secrets out of its workspace. See the [Polish procedure](WINDOWS-QUICKSTART-PL.md) and [evidence](../../Research/codex-windows-sandbox-compatibility-2026-11-05.md).

# Mapping Claude permissions to Codex

Prepared on 2026-10-14 for Codex CLI 0.162.1; re-checked on 2026-10-31 with 0.166.0 (strict profile config loads without errors, a `.env` read is refused under that strict profile). Version-specific statements below were observed on 0.162.1. These examples adapt the course's Claude command and file policies to Codex permission profiles and execpolicy rules. They do not claim tool-for-tool parity. Runtime behavior also depends on the selected sandbox, managed requirements and active session settings.

## Files and sources

| File | Purpose |
|---|---|
| [`../claude/settings.json`](../claude/settings.json) and [`settings.jsonc`](../claude/settings.jsonc) | General Claude source examples |
| [`../../../.claude/settings.json`](../../../.claude/settings.json) | Root Claude source, including file denials and worktree prompts |
| [`config.toml`](config.toml) | Complete reusable Codex configuration |
| [`permissions.toml`](permissions.toml) | Minimal configuration with the same six named permission profiles |
| [`rules/course.rules`](rules/course.rules) | Curated allow, prompt and forbidden command examples |
| [`examples/claude-command-parity.rules`](examples/claude-command-parity.rules) | Inactive literal comparison with every general Claude Bash entry |
| [`../../../.codex/config.toml`](../../../.codex/config.toml) and [`course.rules`](../../../.codex/rules/course.rules) | Active project configuration and rules; currently strict course-root |

Claude's `plansDirectory`, `statusLine`, `pom.xml` hooks and tool names such as `EnterWorktree` are separate features, outside this conversion. Application configuration belongs in the application's own checkout.

## Command rules and approval

Codex uses TOML for configuration and Starlark `.rules` files for command policy. Prefix decisions map from Claude `allow` to `allow`, `ask` to `prompt`, and `deny` to `forbidden`. Overlapping command rules choose `forbidden` before `prompt` before `allow`. Explicit `prompt` rules can request review even when the command would fit inside the sandbox. [Official rules documentation](https://learn.chatgpt.com/docs/agent-configuration/rules), [0.162.1 decision implementation](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/core/src/exec_policy.rs#L396).

An `allow` rule can permit sandbox bypass when the active filesystem policy has no denied-read restrictions. In 0.162.1, active denied reads prohibit unrestricted bypass: approval may widen other access, but the command must retain filesystem enforcement of denied reads. If a suitable sandbox is unavailable, Codex rejects that escalation. This applies to the strict course profiles, which retain denied reads; course-tools has no added deny-read restrictions. It does not govern external apps or erase secrets already inherited through environment variables or outputs. [0.162.1 sandbox implementation](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/core/src/tools/sandboxing.rs#L234).

| Claude command group | Curated Codex decision | Reason |
|---|---|---|
| `pwd`, `whoami` | `allow` | Narrow teaching examples |
| Reads, searches, `which`, `date`, `export`, Git inspection and mutation, package managers, interpreters, builds, tests, Docker inspection and shell wrappers | No explicit command rule | Run inside the sandbox; `on-request` still reviews required escalation |
| `curl`, `wget`, including selected `.exe` names | `prompt` | Explicit review of HTTP destinations and transfer side effects |
| `git` / `git.exe worktree add` | `prompt` | Narrow exception: ask before worktree creation, including inside the sandbox; `git -C <dir> worktree add` does not match this prefix |
| `env`, `printenv` | `forbidden` | Avoid blanket environment dumps |
| Explicit `git push origin/upstream main/master/prod`, upstream-option variants and force-flag prefixes | `forbidden` | Allow participant feature branches while blocking covered protected/force forms |
| `git reset --hard` | `forbidden` for the shown token prefix | Retain destructive-reset denial |
| `chmod`, `chown`, `sudo`, `ssh`, `scp` | `forbidden` | Retain privilege and remote-access denials |
| `rm`, `rmdir`, Docker creation/removal and Compose teardown | `forbidden` for the shown prefixes | Retain course restrictions |
| Blanket `git add -A/--all/.` and `npm install -g/--global` | `forbidden` for the shown prefixes | Stage explicit paths; the project chooses its package manager (Yarn is not blocked) |

The active course policy removes broad read, Git, build, runtime, Docker-inspection and shell-wrapper `prompt` rules: in 0.162.1 they request approval even inside the sandbox, and `auto_review` then spends a reviewer call. Explicit prompts remain for HTTP clients and the narrow worktree-creation prefix. Routine commands and feature-branch pushes have no explicit `allow` or `prompt`; the sandbox supplies the boundary. Do not add broad `allow` rules just to suppress prompts. With `approval_policy = "on-request"` and `approvals_reviewer = "auto_review"`, eligible requests go to the reviewer agent. Routine actions without an approval trigger do not reach it. `approval_policy = "never"` prevents approval requests; it grants no extra access. [Automatic review](https://learn.chatgpt.com/docs/sandboxing/auto-review).

### Prefix and shell limits

The Playwright host exceptions match command prefixes, not safe option sets. For example, `snapshot --filename` can write outside the workspace, and `open --profile`, `--persistent` or `--config` can select additional browser state or configuration. The rules do not limit URLs, output paths or configuration code. Use only owned course sessions, synthetic data and reviewed options. If those restrictions must be enforced, use a reviewed wrapper or require approval instead of treating these prefixes as read-only isolation.

Patterns match argv positions, not arbitrary command substrings. A `["git", "push", ...]` prefix does not match `git -C . push`; that form now has no explicit command rule and remains subject to the sandbox. Likewise `git reset HEAD --hard` does not match the exact destructive-reset prefix. A `*` string in a command pattern is a literal token. Aliases, absolute executable paths, `.exe` names and reordered options need explicit consideration. These examples are not an exhaustive command firewall.

Supported simple shell chains may be split for evaluation; complex scripts can remain a wrapper invocation. PowerShell cmdlets usually occur in script text rather than executable argv. An approved wrapper can perform actions that direct prefix rules forbid, although active filesystem denied reads must remain enforced in 0.162.1. Review the entire script. Do not install the inactive literal comparison alongside the curated policy: both would be evaluated, and its broad allowances have different approval semantics.

### Feature-branch pushes and protected branches

Participants may push their own feature branches and open PRs. The active rules deny explicit pushes to `main`, `master` and `prod` on `origin`/`upstream`, including `-u`/`--set-upstream` before or after the remote, plus `--force`, `-f` and `--force-with-lease` in the documented prefix positions. Ordinary pushes are unmatched, so they need no extra reviewer call when sandbox and network permissions already permit them; blocked network or filesystem access still needs `on-request` escalation. The inactive Claude comparison uses the same bounded push approximation while retaining its other literal allow/deny mappings.

| Tool | Rule form | Limits |
|---|---|---|
| Claude Code | `Bash(git push * main)` / `Bash(git push * main *)` and `Bash(git push *:main)` / `Bash(git push *:main *)`, repeated for `master`/`prod`; force prefixes and globs | `*` includes spaces; bare `git push` has no branch to match; aliases, wrappers and alternate refs/options need separate handling |
| OpenCode | `permission.bash` deny entries for `git push * main` / `git push * main *` and `git push *:main` / `git push *:main *`, repeated for `master`/`prod`; leading and later force globs | Last matching rule wins; bare push only asks, and aliases, wrappers, full refs, global options and `+` refspecs can escape the globs |
| Copilot CLI 1.0.88 | `--deny-tool='shell(git push origin main:*)'`, upstream-option and known-remote variants, plus force-flag prefixes | Primary docs and local help establish trailing `:*` command-stem prefixes, not arbitrary interior globs; bare push, refspec destinations, other remotes, reordered options and later force flags can miss them |
| Codex | `prefix_rule(pattern=[["git","git.exe"],"push",["origin","upstream"],["main","master","prod"]], decision="forbidden", ...)`, upstream-option and force-prefix variants | Token-prefix matching cannot express arbitrary refspec suffixes such as `HEAD:main`; bare push, full refs, `+` refspecs, other remotes, `git -C`, later force flags and `--force-with-lease=<value>` can miss the rules |

These client rules express the course policy; GitHub/Bitbucket branch protection is the real guard for protected branches and force pushes. Configure it in the exercise repository rather than treating a client deny list as complete enforcement. The headless review script retains its blanket push denial. [Claude wildcard syntax](https://code.claude.com/docs/en/permissions), [Copilot permission patterns](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference#tool-permission-patterns).

## Filesystem profiles

`course-workspace` extends `:workspace`. This baseline permits reads across the filesystem, writes in workspace roots and temporary directories, and protects metadata paths such as `.git`, `.agents`, `.codex` and `.aws` from ordinary writes. The course adds denied reads for specific names inside workspace roots; it is not a universal secret detector. For example, `.env.staging` and unrelated credentials elsewhere require separate policy. [Official permission profiles](https://learn.chatgpt.com/docs/permissions), [protected metadata source](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/protocol/src/permissions.rs#L41).

| File case | Course setting |
|---|---|
| Root `.env`, `.env.local`, `.env.dev`, `.env.prod`, `.env.test` | Exact `deny` entries under `filesystem.":workspace_roots"` |
| Nested files with the same names | Corresponding recursive `deny` globs |
| `secrets` | Exact root denial plus `**/secrets/**` |
| `.env.example` | Exact `read` entry for the synthetic template |
| Logs and teaching examples | Remain readable and searchable |
| Review session | `course-review` sets workspace `"." = "read"` |
| Documentation session | `course-docs` additionally grants `docs` write access |

A filesystem `deny` blocks both reads and writes by sandboxed programs, including `rg`, `grep`, `cat` and Python. It cannot express "forbid a full-file Read tool but permit shell searches of the same file". The root examples leave logs and teaching examples accessible when requested. `course-root` is an equivalent named preset for the course repository, not a stronger policy. Review/docs profiles retain inherited writable temporary directories.

Linux/WSL and native Windows pre-expand deny globs into a snapshot of existing matches for their native sandbox enforcement. `glob_scan_max_depth = 12` bounds that scan; it is not a guarantee for deeper paths or paths created after the snapshot. Core tool validators also check the patterns directly. Keep exact denials alongside recursive globs: absent exact paths receive protection that a snapshot-only glob may not provide. [Linux snapshot implementation](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/linux-sandbox/src/bwrap.rs#L495), [Windows scan bounds](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/protocol/src/permissions/windows_glob.rs#L1).

### Empty files visible inside the Linux sandbox

Exact denied paths that do not exist can appear as zero-byte inaccessible files, including a bare `secrets` file. Protected metadata names can appear as empty read-only directories. These are synthetic bubblewrap mount targets, not evidence that a secret file was created. `.aws` is also an intentional Codex-protected metadata name; it need not come from another tool. [Mask construction](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/linux-sandbox/src/bwrap.rs#L1286).

A 2026-10-14 inspection of `/proc/self/mountinfo` showed tmpfs masks at all five denied environment names and `secrets`, and read-only tmpfs directories at `.agents` and `.aws`. Git inside the sandbox reported the bare `secrets` mask as untracked. Do not infer host contents or delete paths from this masked view. Codex tracks synthetic targets and cleans eligible ones after bubblewrap exits, while preserving real pre-existing data. [Lifecycle and cleanup](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/linux-sandbox/src/linux_run_main.rs#L587).

Keep the exact denials. No `.gitignore` entry is needed merely to hide a temporary sandbox view. If a path remains in an ordinary terminal after all sessions using that workspace exit, inspect its metadata outside the sandbox and investigate cleanup before any human-approved removal. Never delete `.env` files based on their apparent size inside the sandbox.

### Bounded log inspection

Search filenames or counts first, then request bounded excerpts. For example:

```bash
rg -n -m 20 --max-columns 200 --max-columns-preview 'ERROR|WARN' logs | head -n 80
```

```bash
tail -n 80 logs/application.log
```

`rg -m` limits matches per file, while `head` limits total returned lines. On PowerShell use `Select-Object -First 80` instead of `head`. These are context-management conventions, not permission boundaries.

`tool_output_token_limit = 4000` supplies a default history-truncation budget for tool results. Tool metadata can override it, and raw rollout payloads are retained. It does not cap the bytes a command reads, prevent full-file reads, guarantee every result is below 4000 tokens, or prevent many outputs accumulating. [0.162.1 output handling](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/core/src/context_manager/history.rs#L554).

## Network and hosted tools

The optional course-tools profile enables command network access with `network.enabled = true`; the reusable user baseline selects `:workspace`. Both user examples leave `features.network_proxy` disabled. Domain tables do not constrain direct destinations without an active proxy (see [optional proxy setup](#project-and-user-proxy-activation)). If separately enabled and validated, the proxy accepts `domains."*" = "allow"` for public hosts; the global wildcard is valid for allows, not denies. Its local/private destination guards do not protect unproxied connections. The course baseline is not an offline or two-host policy. [Network settings](https://learn.chatgpt.com/docs/permissions#network-permissions), [0.162.1 wildcard implementation](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/network-proxy/src/policy.rs#L207).

Only one permission profile is selected for the session. `course-root`, `course-review` and `course-docs` inherit the public network allowance. Merely defining `course-jetbrains` does not activate it. That optional profile extends `:workspace` independently, repeats file protections and permits `blog.jetbrains.com` and `www.jetbrains.com`. Inheriting the default course profile would merge and retain its global allowance. Other destinations can require approval when the proxy is active.

Allowed connections do not automatically trigger the reviewer. The `curl`/`wget` prompt rules review matching command invocations, not every connection by every client. Hosted search, page-opening tools, MCP servers, apps and browser/computer tools have separate controls. Cached web search is a separate capability; `tools.web_search.allowed_domains` is not a universal fetch restriction. [Network scope](https://learn.chatgpt.com/docs/permissions#what-the-network-proxy-does-not-control).

## Load the examples and inspect the effective policy

1. Merge the complete `config.toml` or minimal `permissions.toml` into a trusted project's `.codex/config.toml`. Preserve existing provider choices. Place curated rules under that project's `.codex/rules/` or deliberately under `~/.codex/rules/` for user-wide scope.
2. Set `default_permissions` to one of the six course profile names. These are distinct from model/provider `--profile` presets.
3. Avoid mixing legacy `sandbox_mode` selectors with named-profile selectors. In 0.162.1 the higher-precedence layer that selects `sandbox_mode` or `default_permissions` determines the syntax; at the same layer `default_permissions` wins. A lower-precedence user `sandbox_mode` does not automatically override a trusted project's profile selection. Explicit `--sandbox` can select legacy behavior. Remove obsolete legacy settings deliberately rather than assuming they always win. [Selection implementation](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/core/src/config/mod.rs#L2593).
4. After active work has stopped, run `codex app-server daemon restart` from normal host PowerShell, check `codex app-server daemon version`, and start a **new** ordinary `codex` chat. Do not resume the old chat for this acceptance test: saved thread settings may restore the previous profile. Then inspect `/permissions`, `/status` and `codex doctor --all`. Doctor describes its invocation configuration; it does not inspect every running thread override. Managed requirements and saved session state can also affect the result.

### Windows prompts and prerequisites

The legacy `elevated` sandbox uses administrator-approved provisioning, separate lower-privilege users and firewall rules. The setup helper uses Windows `runas`, which can show UAC; sandbox commands themselves do not become administrator processes. Provisioning is normally reused, but missing or incompatible setup/account state may require repair and another administrator prompt. Ordinary ACL refresh explicitly avoids UAC. Do not promise "exactly once forever". [Windows sandbox documentation](https://learn.chatgpt.com/docs/windows/windows-sandbox), [UAC launch and refresh source](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/windows-sandbox-rs/src/setup.rs#L965).

A Windows Defender Firewall "allow access" dialog is separate from UAC and from Codex command approvals. The managed proxy binds local TCP listeners, so a firewall dialog naming the Codex executable could be related, but the actual dialog's executable and network profile are needed to confirm that cause. A rule tied to a versioned WindowsApps executable path may need revisiting after an app update; recurrence for this machine is UNCONFIRMED. Codex's own sandbox firewall rules use stable identifiers and user scopes, so an app update does not prove that all sandbox rules are recreated. [Proxy listeners](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/network-proxy/src/proxy.rs#L390), [idempotent firewall setup](https://github.com/openai/codex/blob/rust-v0.162.1/codex-rs/windows-sandbox-rs/src/setup_provisioning/firewall.rs#L33).

Codex `prompt` approvals can recur for new actions or destinations, subject to approval caching and saved rules. Auto-review handles eligible requests but cannot approve Windows UAC or firewall dialogs. `unelevated` cannot enforce these denied-read profiles. Current Windows docs describe MXC as an alternative without elevated provisioning; compatibility and its different local-network behavior require separate validation before switching a machine. Keep a working provisioned backend until an alternative has been validated.

## Doctor warnings and validation

On 2026-10-14, Linux CLI 0.162.1 loaded the active course profile with 12 denied-read rules, 6 deny globs, depth 12 and no course-attributable startup warning. The captured Windows alpha doctor likewise reported restricted filesystem, enabled network, `OnRequest`, elevated provisioning complete and denied-read support. This is configuration/provisioning evidence, not a complete native runtime enforcement test.

An `mcp_servers.context7.type is ignored` warning indicates an obsolete `type` key; HTTP transport is selected by `url`. Fix that key in the configuration layer that supplies it. Likewise, a native Windows MCP command cannot use a WSL-only executable path: configure a native path or disable the unused server. Do not fix user-level warnings by loosening project permissions.

Defender exclusions, a non-Dev-Drive worktree, desktop updates and rollout/state-DB discrepancies are environment diagnostics. They are not fixed by loosening course denials. Defender advice is not proof that Defender blocked execution; exclusions and moving repositories require a separate operational decision. The Notes entry "filesystem restricted - network enabled" describes the intentional policy. An idle background server and missing optional databases are not automatically failures.

Validate TOML with `tomllib`, compare all three `permissions` tables, run `codex execpolicy check` against each rule file to exercise inline examples, and inspect `git diff --check`. Policy checks do not execute the checked target commands. A full live enforcement claim additionally requires synthetic runtime probes on each target OS.

```text
codex execpolicy check --pretty --rules .codex/rules/course.rules -- pwd
```

```text
codex execpolicy check --pretty --rules .codex/rules/course.rules -- git push --force origin main
```

```text
codex execpolicy check --pretty --rules .codex/rules/course.rules -- git -C . push
```

Expected decisions are `allow`, `forbidden`, and no matching rule respectively. "No matching rule" does not grant unsandboxed execution.

## Project and user proxy activation

The tested course baseline and both [user examples](config.toml) leave `network_proxy` disabled. Do not enable it as part of the quickstart. The two-host `course-jetbrains` example requires an active proxy and is not an enforced destination allowlist in this baseline. If your deployment needs proxy-enforced domains, treat user-level activation as a separate configuration and acceptance exercise: merge into the existing `[features]` table, stop active work, restart the daemon, start a new chat, and verify permitted and denied destinations. Background daemon threads do not load the project layer; project/user proxy port mismatches have been reported to cause repeated Windows setup. See [Windows sandbox troubleshooting](../../Research/codex-windows-sandbox-troubleshooting-2026-10-15.md), including public reports #54440 and #54441.
