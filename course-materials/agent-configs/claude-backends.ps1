# ============================================================================
# Claude Code aliases and backend switchers - PowerShell equivalent of
# .bashrc-agents (2026-06). Not a full profile: dot-source it from $PROFILE.
# ============================================================================
# Install: dot-source this from your PowerShell profile so the functions/aliases
# load in every session:
#   notepad $PROFILE        # create it if missing
#   # add this line (adjust the path):
#   . "$HOME\path\to\course-materials\agent-configs\claude-backends.ps1"
#
# Delegate the installation to your AI agent instead of editing $PROFILE by
# hand, for example:
#   "Dot-source course-materials/agent-configs/claude-backends.ps1 from my PowerShell
#    $PROFILE, keep API keys in user environment variables and verify the
#    functions load in a new PowerShell session."
#
# Set your provider keys as user env vars (PowerShell, persists across sessions):
#   [Environment]::SetEnvironmentVariable("OPENROUTER_API_KEY","sk-or-...","User")
#   [Environment]::SetEnvironmentVariable("ZAI_API_KEY","...","User")
#   [Environment]::SetEnvironmentVariable("MIMO_API_KEY","...","User")
# Check the active model inside Claude Code with:  /status
# ----------------------------------------------------------------------------

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

# --- Skip permission prompts -------------------------------------------------
# --dangerously-skip-permissions == --permission-mode bypassPermissions (no
# checks at all) - containers/VMs only. Safer modern modes: auto, acceptEdits,
# dontAsk. See https://code.claude.com/docs/en/permission-modes
function clauded      { claude --dangerously-skip-permissions @args }
function claude-auto  { claude --permission-mode auto @args }          # safer
function claude-edits { claude --permission-mode acceptEdits @args }

# Headless examples (CI / scripts):
#   claude --bare -p "Summarize this file" --allowedTools "Read"
#   claude -p "..." --output-format json | ConvertFrom-Json | % result
#   claude -p "..." --permission-mode dontAsk --allowedTools "Bash(git diff *)"

function Clear-ClaudeBackendEnv {
    $vars = @(
        'ANTHROPIC_BASE_URL','ANTHROPIC_API_KEY','ANTHROPIC_AUTH_TOKEN',
        'ANTHROPIC_CUSTOM_HEADERS','ANTHROPIC_MODEL','ANTHROPIC_DEFAULT_HAIKU_MODEL',
        'ANTHROPIC_DEFAULT_SONNET_MODEL','ANTHROPIC_DEFAULT_OPUS_MODEL'
    )
    foreach ($v in $vars) { Remove-Item "Env:$v" -ErrorAction SilentlyContinue }
}

# Anthropic native (default account/login)
function claude-native {
    Clear-ClaudeBackendEnv
    if (-not $env:ANTHROPIC_API_KEY -and $env:ANTHROPIC_KEY) { $env:ANTHROPIC_API_KEY = $env:ANTHROPIC_KEY }
    claude @args
}

# OpenRouter (default: deepseek/deepseek-v4-pro). Override: $env:CLAUDE_CODE_MODEL
function claude-or {
    Clear-ClaudeBackendEnv
    $m = if ($env:CLAUDE_CODE_MODEL) { $env:CLAUDE_CODE_MODEL } else { $null }
    $env:ANTHROPIC_BASE_URL    = "https://openrouter.ai/api"
    $env:ANTHROPIC_API_KEY     = ""
    $env:ANTHROPIC_AUTH_TOKEN  = $env:OPENROUTER_API_KEY
    $env:ANTHROPIC_CUSTOM_HEADERS = "HTTP-Referer: https://openrouter.ai, X-Title: Claude Code via PowerShell"
    $env:ANTHROPIC_DEFAULT_SONNET_MODEL = if ($m) { $m } else { "deepseek/deepseek-v4-pro" }
    $env:ANTHROPIC_DEFAULT_OPUS_MODEL   = if ($m) { $m } else { "z-ai/glm-5.2" }
    $env:ANTHROPIC_DEFAULT_HAIKU_MODEL  = if ($m) { $m } else { "deepseek/deepseek-v4-flash" }
    $env:CLAUDE_CODE_SUBAGENT_MODEL     = if ($m) { $m } else { "deepseek/deepseek-v4-pro" }
    claude @args
}

# Z.ai Coding Plan (default: GLM-5.2). Override: $env:CLAUDE_CODE_MODEL
function claude-zai {
    Clear-ClaudeBackendEnv
    $m = if ($env:CLAUDE_CODE_MODEL) { $env:CLAUDE_CODE_MODEL } else { $null }
    $env:ANTHROPIC_BASE_URL   = "https://api.z.ai/api/anthropic"
    $env:ANTHROPIC_API_KEY    = ""
    $env:ANTHROPIC_AUTH_TOKEN = $env:ZAI_API_KEY
    $env:ANTHROPIC_DEFAULT_SONNET_MODEL = if ($m) { $m } else { "GLM-5.2" }
    $env:ANTHROPIC_DEFAULT_OPUS_MODEL   = if ($m) { $m } else { "GLM-5.2" }
    $env:ANTHROPIC_DEFAULT_HAIKU_MODEL  = if ($env:CLAUDE_CODE_HAIKU_MODEL) { $env:CLAUDE_CODE_HAIKU_MODEL } else { "GLM-4.7" }
    $env:API_TIMEOUT_MS = "3000000"
    claude @args
}

# Xiaomi MiMo Token Plan (default: mimo-v2.6-pro). Override: $env:CLAUDE_CODE_MODEL
function claude-mimo {
    Clear-ClaudeBackendEnv
    $m = if ($env:CLAUDE_CODE_MODEL) { $env:CLAUDE_CODE_MODEL } else { $null }
    $env:ANTHROPIC_BASE_URL   = "https://token-plan-ams.xiaomimimo.com/anthropic"
    $env:ANTHROPIC_API_KEY    = ""
    $env:ANTHROPIC_AUTH_TOKEN = $env:MIMO_API_KEY
    $env:ANTHROPIC_MODEL      = "mimo-v2.6-pro"
    $env:ANTHROPIC_DEFAULT_SONNET_MODEL = if ($m) { $m } else { "mimo-v2.6-pro" }
    $env:ANTHROPIC_DEFAULT_OPUS_MODEL   = if ($m) { $m } else { "mimo-v2.6-pro[1m]" }
    $env:ANTHROPIC_DEFAULT_HAIKU_MODEL  = if ($env:CLAUDE_CODE_HAIKU_MODEL) { $env:CLAUDE_CODE_HAIKU_MODEL } else { "mimo-v2.6-flash" }
    $env:CLAUDE_CODE_SUBAGENT_MODEL     = if ($m) { $m } else { "mimo-v2.6-flash" }
    claude @args
}

# Ollama local/cloud (default: glm-5.2:cloud). Override: $env:CLAUDE_CODE_MODEL
function claude-ollama {
    Clear-ClaudeBackendEnv
    $m = if ($env:CLAUDE_CODE_MODEL) { $env:CLAUDE_CODE_MODEL } else { $null }
    $env:ANTHROPIC_BASE_URL   = if ($env:OLLAMA_ANTHROPIC_BASE_URL) { $env:OLLAMA_ANTHROPIC_BASE_URL } else { "http://localhost:11434" }
    $env:ANTHROPIC_API_KEY    = ""
    $env:ANTHROPIC_AUTH_TOKEN = if ($env:OLLAMA_ANTHROPIC_AUTH_TOKEN) { $env:OLLAMA_ANTHROPIC_AUTH_TOKEN } else { "ollama" }
    $env:ANTHROPIC_DEFAULT_SONNET_MODEL = if ($m) { $m } else { "glm-5.2:cloud" }
    $env:ANTHROPIC_DEFAULT_OPUS_MODEL   = if ($m) { $m } else { "glm-5.2:cloud" }
    $env:ANTHROPIC_DEFAULT_HAIKU_MODEL  = if ($env:CLAUDE_CODE_HAIKU_MODEL) { $env:CLAUDE_CODE_HAIKU_MODEL } else { "glm-5.2:cloud" }
    claude @args
}

Set-Alias ccn  claude-native
Set-Alias cco  claude-or
Set-Alias ccz  claude-zai
Set-Alias ccm  claude-mimo
Set-Alias ccol claude-ollama
