# Agent config examples

Example configurations for the agents used in the course. The repository root holds project settings (filesystem/network permissions, MCP servers) and curated command rules. Provider profiles and sub-agents live here: copy the ones you need and adapt them. Writing your own sub-agent from one of these is a course exercise.

Each folder has the shape of that tool's own config folder.

| Folder | What it holds | Where it goes |
|---|---|---|
| `codex/` | `config.toml`, `permissions.toml`, `PERMISSIONS.md`, curated `rules/` and inactive comparison in `examples/`, provider profiles `<name>.config.toml` for Ollama, OpenRouter and Z.ai with `models.zai.json`, sub-agents in `agents/` | `~/.codex/` for the config and the profiles; `.codex/agents/` in your project for the sub-agents |
| `claude/` | `settings.json` (and a commented `settings.jsonc`), `CLAUDE.md`, `statusline.sh`, sub-agents in `agents/`, `mcp-jetbrains.json` (JetBrains MCP server for a default Windows install of IntelliJ IDEA 2025.3.3; set the path of your own IDE) | `~/.claude/` for settings, `CLAUDE.md` and the status line; `.claude/agents/` in your project for the sub-agents |
| `copilot/` | start scripts with allowed and denied tools, a custom agent in `agents/` | run the script from the repository root; `.github/agents/` in your project for the agent |
| `jetbrains-ai-assistant/` | `.aiassistant/rules/pom-security.md`, a project rule for `pom.xml` files, see its README | copy `.aiassistant/` to your repository root |
| `microsoft-365-copilot/` | the Repository Checker agent from Microsoft 365 Copilot Agent Builder: package ZIP, unpacked definition and two skills, one with a Python script | recreate it in Agent Builder; copy the skills to `.github/skills/` for GitHub Copilot |
| `opencode/` | `opencode.jsonc` with a default model, MCP servers and Bash push permissions | `~/.config/opencode/` or your project root |
| `.bashrc-agents`, `claude-backends.ps1`, `codex-aliases.ps1` | shell aliases and functions for Claude Code and Codex: permission modes, backend switchers, Codex profiles | source `.bashrc-agents` from `~/.bashrc`; dot-source the `.ps1` files from PowerShell `$PROFILE` |

Install the shell aliases by delegating to your AI agent rather than editing `~/.bashrc` or `$PROFILE` by hand; each file has an example prompt in its header. Keep API keys out of these files.

## Logging in on a course VM, WSL or SSH

The browser on your own computer cannot hand the login back to a VM, so log in with a code. Open every link on your own computer, not inside the VM, and keep your phone at hand: both providers verify a mobile number when a new account first signs in.

- **Codex CLI:** run `codex login --device-auth`, open the URL on your own computer, sign in and enter the one-time code. Then start `codex` and run one prompt. If you see "contact your workspace admin to enable device code authentication", tell the trainer: the workspace owner must switch on device code sign-in.
- **Claude Code CLI:** run `claude`, then `/login` (or `claude auth login`). Open the URL (press `c` to copy it), sign in, copy the code the browser shows and paste it at "Paste code here if prompted". In Windows Terminal use right-click or Shift+Insert if Ctrl+V does nothing.
- **Claude Desktop app:** choose the e-mail login, not "Continue with Google". Open the link from the e-mail on your own computer, cancel the prompt to open the Claude app, copy the code from the page and paste it into the app on the VM.
- If your address already belongs to an employer Claude or ChatGPT organization, pick the training organization or workspace after signing in.
- **Activate in the browser first.** Accept the invitations and finish the first login on the provider's web page on your own computer, then log in to the CLI or desktop app. In Claude, check the account shown at the bottom of the screen: it must be the course address you were invited with. A code or link from the e-mail stays valid for about 10 minutes.
- Use the address you were invited with for each provider. When the trainer gives you a course alias for Claude, do not use it to log in to ChatGPT.
- Sprawdź logowanie CLI i aplikacji desktopowej osobno; nie zakładaj, że logowanie jednego klienta automatycznie wystarczy drugiemu.

### A course account next to your company account

Na VM zachowaj katalogi `CLAUDE_CONFIG_DIR` i `CODEX_HOME` skonfigurowane pod `D:\AI\labuser` oraz repozytorium `D:\jsystems-claude-codex-gis-2026-11`. Nie przenoś istniejącego logowania do nowego katalogu.

Na własnym komputerze oddziel konto firmowe i kursowe przez osobne katalogi konfiguracji: [drugi CODEX_HOME](codex/separate-course-account/README.md) dla Codex oraz [CLAUDE_CONFIG_DIR](https://code.claude.com/docs/en/authentication) dla Claude Code. Pierwsze uruchomienie z nowym katalogiem wymaga logowania. Nie używaj konta kursowego do kodu ani danych firmowych.

## Claude Code statusline and cache hit rate

The updated [statusline.sh](claude/statusline.sh) shows the model with its version, a `1M` tag for an extended context window, the reasoning effort (`xhigh` orange, `max` red), context usage, cost estimate, subscription usage and `Cache: 88%(✕52m)`. Copy it to `~/.claude/statusline.sh` when using the shipped Claude configuration. It requires Bash and `jq`.

The `✕52m` countdown shows when the cached prefix expires (TTL 5m or 1h); the first request after that re-sends the whole context at full price, so send your next prompt before it runs out. It turns orange under 5 minutes and shows `(cold)` once expired. The countdown only moves when the script re-runs, so the shipped [settings.json](claude/settings.json) sets `"refreshInterval": 30` on `statusLine`; without it the status line refreshes only on session events and freezes while you are idle.

Cache data requires Claude Code **2.1.251+** and appears after the main conversation receives an API response. The script displays `prompt_cache.hit_ratio * 100`, rounded to a whole percent. This is the share of input tokens read from cache across the main conversation, including cache reads, writes and uncached input in the denominator; subagents are excluded. It is not the percentage of requests served from cache or a percentage discount on the whole bill. See the [official prompt-cache fields](https://code.claude.com/docs/en/statusline#prompt-cache-fields).

A hit rate of 90% or more is green, 70-89% orange and under 70% red: a long session with a stable prefix sits above 90%, and only the first requests (the initial cache write) are naturally lower. Missing or null data hides the cache segment; a real zero is shown as `Cache: 0%`. Check `/usage` and its `Prompt cache (main)` line if the segment is absent. Earlier Claude Code versions do not provide this field.

Run the script with a synthetic payload to see the output without starting a paid model request:

```bash
printf '%s' '{"model":{"id":"claude-sonnet-example","display_name":"Sonnet"},"workspace":{"current_dir":"/tmp/course-demo"},"context_window":{"used_percentage":25},"prompt_cache":{"hit_ratio":0.88}}' | bash course-materials/agent-configs/claude/statusline.sh
```

## Statusline and concise output

The shipped [statusline.sh](claude/statusline.sh) already supports the main-conversation prompt-cache hit rate. Keep this version rather than replacing it with an older course copy. It requires Bash and jq; start with `jq --version`, then use `/statusline` to request a reviewed setup based on that script. Run the synthetic-JSON example in [token-budget exercises](../Research/agent-workflows-and-token-budget-2026-10-24.md) before enabling it. That note also covers `/config`, usage aliases, code-login limitations and optional analytics.

## Protected-branch push policy

Participants may push their own branches and open PRs. The examples deny the covered pushes to `main`, `master` and `prod` and force-push forms; Claude, Copilot and OpenCode may still ask before ordinary pushes, while curated Codex rules leave them to sandbox permissions and `on-request` escalation. These patterns cover common spellings, not every Git invocation.

| Tool | Example file | Block push to main/master/prod | Block force push | What the tool cannot match with these rules |
|---|---|---|---|---|
| Claude Code | [settings.json](claude/settings.json), [settings.jsonc](claude/settings.jsonc) | `Bash(git push * main)` / `Bash(git push * main *)` and `Bash(git push *:main)` / `Bash(git push *:main *)`, repeated for `master`/`prod` | `Bash(git push --force:*)`, `Bash(git push -f:*)`, `Bash(git push --force-with-lease:*)` and later-position force globs | Bare `git push` on a checked-out protected branch; aliases, wrappers, full refs, global options and `+` force refspecs |
| Codex | [rules/course.rules](codex/rules/course.rules) | `prefix_rule(pattern=[["git","git.exe"],"push",["origin","upstream"],["main","master","prod"]], decision="forbidden", ...)`, plus upstream-option variants | Forbidden prefixes for `--force`, `-f`, `--force-with-lease` in documented positions | Bare protected-branch push; token prefixes cannot match `HEAD:main` refspecs, other remotes/options, arbitrary later force flags or `--force-with-lease=<value>` |
| Copilot CLI | [start-copilot.sh](copilot/start-copilot.sh), [start-copilot.ps1](copilot/start-copilot.ps1) | `--deny-tool='shell(git push origin main:*)'`, repeated for `upstream`, `master`/`prod` and upstream-option variants | `shell(git push --force:*)`, `shell(git push -f:*)`, `shell(git push --force-with-lease:*)` and known-position variants | Bare protected-branch push; trailing command-stem prefixes miss refspec destinations, other remotes/options and arbitrary later force flags |
| OpenCode | [opencode.jsonc](opencode/opencode.jsonc) | `permission.bash` entries `"git push * main": "deny"` / `"git push * main *": "deny"` and `"git push *:main": "deny"` / `"git push *:main *": "deny"`, repeated for `master`/`prod` | `"git push --force*": "deny"`, standalone `-f` patterns and later-position force globs | Bare protected-branch push only asks; aliases, wrappers, full refs, global options and `+` force refspecs can escape the globs |

GitHub/Bitbucket branch protection is the real guard for protected branches and force pushes; the headless review agent retains its blanket push denial.

## GitHub repository deletion

The root Claude settings and the Claude examples deny direct `gh repo delete` calls and commands mentioning `delete_repo`. The root Codex policy and its example deny `gh repo delete` (including `gh.exe`) and request approval for `gh auth login` and `gh auth refresh`. A Codex approval prompt is not a ban on granting a scope. The inactive parity example uses the same deletion rules.

These patterns cover direct CLI calls, not every API call, wrapper or credential. Do not grant repository-deletion privileges to course agents. Inspect token permissions and repository roles separately; classic OAuth `delete_repo` is not the only possible way to authorize deletion. See the [GitHub CLI deletion reference](https://cli.github.com/manual/gh_repo_delete) and [Claude permission precedence](https://code.claude.com/docs/en/permissions).

## Ctrl+G: długi prompt w edytorze

W Claude Code i Codex CLI naciśnij Ctrl+G podczas pisania promptu, aby otworzyć jego bieżącą treść w zewnętrznym edytorze. Oba narzędzia wybierają `VISUAL`, a gdy jej nie ustawiono, `EDITOR`. Na kursowych VM jest zainstalowany `micro`: zapisz Ctrl+S, zamknij Ctrl+Q. Po zamknięciu edytora tekst wraca do agenta; przejrzyj go przed wysłaniem.

Windows PowerShell, trwale dla użytkownika:

```powershell
[Environment]::SetEnvironmentVariable('VISUAL', 'micro', 'User')
```

```powershell
[Environment]::SetEnvironmentVariable('EDITOR', 'micro', 'User')
```

Otwórz nowe okno terminala i uruchom agenta ponownie. Aby użyć ustawień także w bieżącym oknie:

```powershell
$env:VISUAL = 'micro'
```

```powershell
$env:EDITOR = 'micro'
```

Linux/macOS: dopisz poniższe eksporty do `~/.bashrc` dla Bash lub `~/.zshrc` dla Zsh, a potem otwórz nowe okno terminala. Poza VM najpierw sprawdź, czy `micro` jest zainstalowany.

```bash
export VISUAL='micro'
```

```bash
export EDITOR='micro'
```

W przykładach profilu PowerShell i [.bashrc-agents](.bashrc-agents) `micro` jest wybierany tylko wtedy, gdy polecenie istnieje. Możesz użyć innego edytora, np. `zed --wait`; edytor musi zaczekać na zamknięcie pliku. Dla porównawczego ćwiczenia Copilot CLI ustaw również `COPILOT_EDITOR` na tę samą wartość w profilu powłoki.

Źródła, sprawdzone 11.11.2026: [Codex CLI: Prompt editor](https://learn.chatgpt.com/docs/cli-customization#prompt-editor), [Claude Code: Ctrl+G](https://code.claude.com/docs/en/interactive-mode#general-controls), [Claude Code: VISUAL i EDITOR, wyjaśnienie maintainera](https://github.com/anthropics/claude-code/issues/18990). Dokumentacja interaktywna Claude potwierdza skrót; kolejność zmiennych potwierdza wyjaśnienie maintainera. Nie przeprowadzono tu interaktywnego testu Ctrl+G na Windows.

## Codex permissions

Start with the [user-wide Windows baseline](codex/README.md#user-wide-windows-baseline). The reusable config examples default to :workspace and include optional course-tools definitions; the current project selects the strict course-root profile. course-tools is an optional profile to install deliberately. Install definitions and reviewed rules at user scope if selecting that profile across repositories.

See [Claude-to-Codex permission mapping](codex/PERMISSIONS.md) for annotated TOML filesystem profiles, command `allow` / `prompt` / `forbidden` rules, and their limits. `codex/config.toml` includes these permissions directly in the main Codex example; `codex/permissions.toml` provides the same profiles as a minimal standalone example. Copy the configuration together with the reviewed `codex/rules/` files. `codex/examples/claude-command-parity.rules` is an inactive syntax comparison with broad allowances; use `codex/rules/course.rules` for the curated course policy.

Both user examples explicitly disable `features.network_proxy` for the tested Windows baseline. Inspect the actual project configuration separately. Do not enable it during the quickstart. Domain tables, including the optional two-host profile, require a separately activated and validated proxy to constrain destinations. See the [optional proxy setup](codex/PERMISSIONS.md#project-and-user-proxy-activation) and [Windows sandbox troubleshooting](../Research/codex-windows-sandbox-troubleshooting-2026-10-15.md).

## Codex profiles

For the measured optional Windows host-tool baseline, see course-tools and its tradeoffs: [participant steps in Polish](codex/WINDOWS-QUICKSTART-PL.md) and [evidence report](../Research/codex-windows-sandbox-compatibility-2026-11-05.md). The full reusable example enables Context7 without a required API key. The active project currently disables it: enable the reviewed Context7 entry in the project too, then verify /mcp. Playwright MCP stays off while the CLI is used for manual QA.

Codex reads profile files only from `~/.codex/`. Copy them there, then choose one:

```bash
cp course-materials/agent-configs/codex/*.config.toml course-materials/agent-configs/codex/models.zai.json ~/.codex/
```

```bash
codex --profile ollama-lfm
```

Check the `model:` and `provider:` lines Codex prints at startup: a profile name without a file is not an error, Codex just runs the default model.

Shell shortcuts: [Bash Codex section](.bashrc-agents) and [PowerShell functions and aliases](codex-aliases.ps1). Dot-source the PowerShell file from `$PROFILE` using its installation comment. The same names cover all six shipped provider profiles: `cdxz` (also `codexz`), `cdxor`, `cdxoc`, `cdxlfm`, `cdxsql`, `cdxgemma`. Copy the profile files to `~/.codex/` first, including `models.zai.json` for Z.ai; the scripts contain no real keys.

Mode aliases, checked against local `codex --help` and `codex resume --help` on 0.162.1 (2026-10-16): `cdxauto` (automatic approval review with workspace-write), `cdxro` (read-only), `cdxnd` (no shared daemon), `cdxwt` (new managed worktree), `cdxlast` (resume last). Combine a mode with `--profile <name>`. `cdxwt` requires worktree authorization under this repository's rules. `cdxyolo` disables both approvals and sandbox: use only inside external disposable isolation without secrets, never as a permissions workaround. [CLI reference](https://developers.openai.com/codex/cli/reference/).

## Sub-agents

- TypeScript and Node.js: `claude/agents/be-developer.md`, `fe-developer.md`, `qa-engineer.md`; `codex/agents/frontend-nextjs-developer.toml`, `e2e-qa-engineer.toml`.
- Java and Spring Boot: `claude/agents/java-be-developer.md` (short) and `java-be-developer-long.md`, `java-fe-developer.md`, `java-qa-engineer.md`; `codex/agents/java-springboot-developer.toml`.
- Code review in Copilot: `copilot/agents/CodeReview.agent.md`.

To use one, copy it into your project (`.claude/agents/`, `.codex/agents/` or `.github/agents/`), replace the stack-specific parts (build tool, test runner, framework) with yours, and adjust the list of skills to the ones you have installed.
