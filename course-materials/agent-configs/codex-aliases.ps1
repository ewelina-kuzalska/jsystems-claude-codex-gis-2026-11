# Codex CLI aliases, profiles and modes - PowerShell equivalent of the Codex
# section in .bashrc-agents (verified: codex-cli 0.162.1 help).
# Dot-source this file from $PROFILE, adjusting the path:
#   . "$HOME\path\to\course-materials\agent-configs\codex-aliases.ps1"
#
# Delegate the installation to your AI agent instead of editing $PROFILE by
# hand, for example:
#   "Dot-source course-materials/agent-configs/codex-aliases.ps1 from my PowerShell
#    $PROFILE, keep API keys in user environment variables and verify the
#    functions load in a new PowerShell session."
# Copy chosen <name>.config.toml files from agent-configs/codex/ to
# $HOME\.codex\ first (or $env:CODEX_HOME when explicitly configured).
# Z.ai also needs models.zai.json beside zai.config.toml.
# Keys belong in provider environment variables, never in this file.
# Confirm the model/provider at startup. @args forwards extra arguments.

# Default editor for CLI tools; preserve the current editor if micro is absent.
if (Get-Command micro -ErrorAction SilentlyContinue) {
    $env:EDITOR = "micro"
    $env:VISUAL = $env:EDITOR
    $env:COPILOT_EDITOR = $env:EDITOR
}
# Alternative: uncomment all three lines for Zed.
# $env:EDITOR = "zed --wait"
# $env:VISUAL = $env:EDITOR
# $env:COPILOT_EDITOR = $env:EDITOR

# Provider routes, including Ollama cloud, may send prompts off-machine.
function Invoke-CodexZai         { codex --profile zai @args }
function Invoke-CodexOpenRouter  { codex --profile openrouter @args }
function Invoke-CodexOllamaCloud { codex --profile ollama-cloud @args }
function Invoke-CodexOllamaLfm   { codex --profile ollama-lfm @args }
function Invoke-CodexOllamaSql   { codex --profile ollama-sql @args }
function Invoke-CodexOllamaGemma { codex --profile ollama-gemma @args }

# Automatic review retains workspace-write and can deny approval requests.
function Invoke-CodexAuto       { codex --approve-for-me @args }
function Invoke-CodexReadOnly   { codex -s read-only @args }
# Use a private foreground server instead of the shared background daemon.
function Invoke-CodexNoDaemon   { codex --no-daemon @args }
# Creates a NEW managed Git worktree: obtain authorization and clean up later.
function Invoke-CodexWorktree   { codex --worktree @args }
# Cwd filtering applies. Confirm which session will be resumed.
function Invoke-CodexLast       { codex resume --last @args }
# DANGER: disables BOTH approvals and sandbox. Only for an externally isolated
# disposable VM/container without secrets or access to host files. The flag
# creates no isolation and must never be used to fix permission errors.
function Invoke-CodexYolo       { codex --dangerously-bypass-approvals-and-sandbox @args }

Set-Alias -Name codexz   -Value Invoke-CodexZai
Set-Alias -Name cdxz     -Value Invoke-CodexZai
Set-Alias -Name cdxor    -Value Invoke-CodexOpenRouter
Set-Alias -Name cdxoc    -Value Invoke-CodexOllamaCloud
Set-Alias -Name cdxlfm   -Value Invoke-CodexOllamaLfm
Set-Alias -Name cdxsql   -Value Invoke-CodexOllamaSql
Set-Alias -Name cdxgemma -Value Invoke-CodexOllamaGemma
Set-Alias -Name cdxauto  -Value Invoke-CodexAuto
Set-Alias -Name cdxro    -Value Invoke-CodexReadOnly
Set-Alias -Name cdxnd    -Value Invoke-CodexNoDaemon
Set-Alias -Name cdxwt    -Value Invoke-CodexWorktree
Set-Alias -Name cdxlast  -Value Invoke-CodexLast
Set-Alias -Name cdxyolo  -Value Invoke-CodexYolo

# Examples: cdxro --profile zai; cdxauto --profile ollama-lfm
