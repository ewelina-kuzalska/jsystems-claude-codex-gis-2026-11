> Aktualizacja 5.11.2026: poniższa historyczna teza, że Codex nie jest w ACP Registry, jest nieaktualna. JetBrains udostępnia Codex przez AI Chat -> wybór agenta -> Install From ACP Registry (IDE 2026.1+ i zgodny plugin). Użyj [oficjalnej instrukcji ACP](https://www.jetbrains.com/help/ai-assistant/acp.html) i [bazy JetBrains](https://youtrack.jetbrains.com/projects/PY/articles/SUPPORT-A-3700/Using-Claude-Codex-and-Cursor-agents-in-JetBrains-IDEs). Nie uruchamiaj `codex acp`: CLI nie ma takiej komendy. Obecny adapter to [agentclientprotocol/codex-acp](https://github.com/agentclientprotocol/codex-acp); stary projekt zed-industries jest archiwalny. ACP nie gwarantuje zgodności funkcji z CLI, a obecna instrukcja JetBrains wyklucza WSL w tej integracji. Dalszą część traktuj jako materiał historyczny.

<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# research and compare Codex CLI with OpenCode. features, capabilities, pros and cons. Can we use multi-agent workflows with sub-agents in both of them? do they have long running tasks and memory as claude code CLI has? can we use any model with good function calling hosted on custom openai compatible endpoint with both of them? (e.g. OpenRouter).

do both have sandboxing and how does it work on windows and on Linux Ubuntu?

both are open source? Codex CLI has rust-based core, yes? while OpenCode is TypeScript? isn't codex faster because of this?

Now I have enough information for a comprehensive comparison. Let me put it together.

***

Both **Codex CLI** and **OpenCode** are open-source AI coding agents for the terminal, but they diverge sharply in architecture philosophy, provider flexibility, and built-in safety features. Here's a deep-dive across every dimension you asked about.

## Open Source Status

Both are fully open source [^1_1][^1_2]. Codex CLI lives at `github.com/openai/codex` (62K stars as of early 2026) [^1_3], while OpenCode is at the `sst/opencode` repo (112K stars, 2.5M monthly active developers) [^1_3]. Both accept community contributions.

## Architecture: Rust Core vs TypeScript

You're correct on both counts. Codex CLI has a **Rust core** (`codex-rs`) that handles the protocol layer, sandboxing, safety enforcement, and agent state management [^1_4][^1_5]. The CLI itself ships via `npm install -g @openai/codex`, but the heavy lifting - execution isolation, Landlock integration, metadata schemas - is compiled Rust running natively [^1_6]. OpenCode is **TypeScript/Node.js**, built with the Vercel AI SDK and a TUI framework [^1_7][^1_8].

Does this make Codex faster in practice? **Somewhat, but for a different reason than you'd expect.** The bottleneck in both tools is LLM API round-trips, not CLI processing. Where Rust gives Codex a measurable edge is:

- **Sandboxing overhead is near-zero** (Landlock calls at the kernel level vs. process wrapping)
- **Richer streaming/rendering** - recent updates added Rust-level metadata on text elements for smoother schema evolution [^1_6]
- **Codex-Spark on Cerebras WSE-3** runs at 1,000+ tokens/sec specifically because the OpenAI infra + Rust protocol are co-designed [^1_3]

OpenCode's TypeScript runtime adds a small, usually imperceptible overhead for non-LLM operations.

## Multi-Agent Workflows \& Sub-Agents

| Feature | Codex CLI | OpenCode |
| :-- | :-- | :-- |
| Native sub-agents | ✅ First-class, documented | ✅ Supported, parallel sessions |
| Spawn mechanism | `spawn_agents_on_csv`, `spawn_agents` tool, `/agent` command | Multiple agent configs with `subagent` mode |
| Parallel workers | ✅ Fan-out via CSV batch jobs with `max_concurrency` | ✅ Multiple agents on same project without conflict |
| Agent inspection | `/agent` to switch/inspect live threads | Manual terminal splits or community tool |
| Configuration | `.codex/agents/` + `config.toml` per-agent | `opencode.json` with per-agent model + prompt |

Codex CLI's multi-agent system is notably more **structured and production-grade** [^1_9][^1_10] - you can define specialized agents (reviewer, planner, coder), spawn them with `spawn_agents_on_csv` for batch work (e.g., review 50 components in parallel), and poll results with the `wait` tool for up to 1 hour per call [^1_9]. The main agent automatically orchestrates, waits, and consolidates [^1_10]. OpenCode's parallel agents are more of a **power-user workflow** - you run multiple sessions or use community tools like `opencode-parallel-agents` [^1_11][^1_12].

## Long-Running Tasks

Codex CLI is explicitly designed for **long-horizon tasks** - OpenAI published a case study of a Codex-tuned model running uninterrupted for ~25 hours on a complex spec, with autonomous milestone verification and lint/test repair loops [^1_13]. (Check current Codex docs for the exact model name.) The `wait` tool's long-polling (up to 1 hour per call) enables this natively [^1_9]. SQLite-backed agent job state means crashes don't lose progress [^1_9].

OpenCode has **SQLite-based session persistence** [^1_7] so conversation history survives restarts, but it doesn't have a native "run for 25 hours autonomously" construct. Long tasks work but require more manual orchestration.

## Persistent Memory

Neither tool has Claude Code-style native cross-session memory out of the box:

- **Codex CLI**: Uses `AGENTS.md` (like Claude Code's `CLAUDE.md`) for static project context. Cross-session memory requires MCP integration (e.g., CORE Memory MCP server or community tools like CogniLayer) [^1_14][^1_15].
- **OpenCode**: Stores conversation history in SQLite, and can read from `.claude/CLAUDE.md` automatically (this can be disabled via `OPENCODE_DISABLE_CLAUDE_CODE` env var) [^1_16]. Also supports MCP for external memory.


## Custom OpenAI-Compatible Endpoints (OpenRouter)

This is a **major differentiator**:

**OpenCode** wins decisively here. It uses the `@ai-sdk/openai-compatible` adapter natively, so connecting to OpenRouter, LLM Gateway, or any compatible endpoint is just a config block [^1_8][^1_17]:

```json
"provider": {
  "openrouter": {
    "npm": "@ai-sdk/openai-compatible",
    "options": {
      "baseURL": "https://openrouter.ai/api/v1",
      "apiKey": "{env:OPENROUTER_API_KEY}"
    }
  }
}
```

You get **75+ providers** including Ollama, AWS Bedrock, Google, and any OpenAI-compatible self-hosted endpoint [^1_7][^1_18]. Note: Anthropic blocked direct OAuth for OpenCode in January 2026, forcing Claude users through OpenRouter or other proxies [^1_3].

**Codex CLI** is architected as an **OpenAI-first product**. While it authenticates via OpenAI account and the system prompts + tool schemas are tuned specifically for the current Codex model behavior, OpenRouter works - but you sacrifice the model-specific optimization that makes Codex performant [^1_3]. (Model lineup and OpenRouter support change often - check current Codex docs.) There's no first-class `@ai-sdk/openai-compatible`-style adapter. If you want full model freedom, OpenCode is the better choice.

## Sandboxing

### Codex CLI - Built-in, Kernel-Level

Codex CLI has **first-class sandboxing built into the Rust core** [^1_19][^1_5]:

- **Linux**: Uses **Landlock** (Linux Security Module, kernel 5.13+) for filesystem restriction. Can mount paths read-only, block network, restrict writes to workspace [^1_6][^1_19]. Modes: `--sandbox read-only`, `--sandbox workspace-write`, `--sandbox danger-full-access`
- **Windows**: Uses `WindowsRestrictedToken` (experimental, toggled via `experimental_windows_sandbox`) [^1_4][^1_5] - less mature than Linux
- **macOS**: seatbelt (App Sandbox)

On **Ubuntu specifically**, Landlock is the mechanism - it's transparent, low-overhead, and enforced at the kernel level. No container needed.

### OpenCode - External Plugin Only

OpenCode has **no built-in sandboxing** [^1_20][^1_21]. Your options:

- **`opencode-sandbox` npm plugin** (community): Uses `@anthropic-ai/sandbox-runtime` - seatbelt on macOS, **bubblewrap on Linux** [^1_22]. Configurable filesystem allow/deny lists and network domain filtering via `.opencode/sandbox.json` [^1_22]
- **Docker** (recommended for both platforms): Run OpenCode inside a container [^1_23][^1_24]
- **Windows**: No native sandboxing at all - Docker or Hyper-V VM is the only real option

OpenCode also had a notable **unauthenticated RCE vulnerability** discovered in January 2026 [^1_25], highlighting that security is not a core design priority the way it is in Codex CLI.

## Quick Reference

| Dimension | Codex CLI | OpenCode |
| :-- | :-- | :-- |
| Language | Rust core + npm shell | TypeScript/Node.js |
| Stars (2026) | 62K | 112K |
| Default model | GPT-5.x Codex family (check current default) | Any (75+ providers) |
| OpenRouter/custom endpoint | Possible, non-native | ✅ First-class support |
| Multi-agents | ✅ Native, structured | ✅ Parallel sessions |
| Long-running tasks | ✅ Native (25h+ tested) | Possible, less structured |
| Cross-session memory | Via MCP only | SQLite + CLAUDE.md + MCP |
| Sandboxing (Linux) | ✅ Landlock (kernel-level) | bubblewrap via plugin / Docker |
| Sandboxing (Windows) | ⚠️ Experimental token | Docker only |
| Security track record | Solid | RCE vuln (Jan 2026) |
| Provider lock-in | OpenAI-first | None |

**Bottom line for your use case**: If you want to use OpenRouter or self-hosted models with good function calling, **OpenCode is clearly better**. If you're on OpenAI and need robust built-in sandboxing, long-horizon autonomous runs, and a production-grade multi-agent system, **Codex CLI is the stronger choice** - and yes, the Rust core gives it a real edge in sandboxing performance and streaming fidelity.
<span style="display:none">[^1_26][^1_27][^1_28][^1_29][^1_30][^1_31][^1_32][^1_33][^1_34][^1_35][^1_36][^1_37][^1_38][^1_39][^1_40][^1_41][^1_42][^1_43][^1_44][^1_45]</span>

<div align="center">⁂</div>

[^1_1]: https://github.com/openai/codex

[^1_2]: https://opencode.ai

[^1_3]: https://www.morphllm.com/comparisons/opencode-vs-codex

[^1_4]: https://fossies.org/linux/codex-rust/codex-rs/core/src/safety.rs

[^1_5]: https://fossies.org/linux/codex-rust/codex-rs/core/src/sandboxing/mod.rs

[^1_6]: https://www.reddit.com/r/CodexAutomation/comments/1qdetsx/codex_cli_updates_0810_0840_gpt52codex_default/

[^1_7]: https://yuv.ai/learn/opencode-cli

[^1_8]: https://help.apiyi.com/en/opencode-api-proxy-configuration-guide-en.html

[^1_9]: https://developers.openai.com/codex/multi-agent/

[^1_10]: https://developers.openai.com/codex/concepts/multi-agents/

[^1_11]: https://github.com/aptdnfapt/opencode-parallel-agents

[^1_12]: https://www.reddit.com/r/opencodeCLI/comments/1r3cxwh/explain_to_me_parallel_agents_what_is_the_purpose/

[^1_13]: https://developers.openai.com/blog/run-long-horizon-tasks-with-codex/

[^1_14]: https://www.reddit.com/r/OpenAI/comments/1nr1icf/how_to_give_codex_cli_temporal_memory_that/

[^1_15]: https://www.reddit.com/r/ClaudeAI/comments/1rhjc7f/i_built_a_persistent_memory_for_claude_code_it/

[^1_16]: https://opencode.ai/docs/cli/

[^1_17]: https://llmgateway.io/guides/opencode

[^1_18]: https://slashdot.org/software/comparison/Codex-CLI-vs-opencode/

[^1_19]: https://github.com/openai/codex/blob/main/codex-rs/README.md

[^1_20]: https://www.reddit.com/r/opencodeCLI/comments/1riizl1/sandboxed_opencode/

[^1_21]: https://www.reddit.com/r/opencodeCLI/comments/1rgmh3t/do_you_run_opencode_in_a_sandboxed_environment_or/

[^1_22]: https://libraries.io/npm/opencode-sandbox

[^1_23]: https://docs.docker.com/ai/sandboxes/agents/opencode/

[^1_24]: https://www.reddit.com/r/LocalLLaMA/comments/1ozre04/comment/npdpam5/

[^1_25]: https://news.ycombinator.com/item?id=46581095

[^1_26]: https://developers.openai.com/codex/cli/features/

[^1_27]: https://developers.openai.com/codex/cli/

[^1_28]: https://marketbetter.ai/blog/openai-codex-cli-gtm-guide/

[^1_29]: https://www.deployhq.com/blog/comparing-claude-code-openai-codex-and-google-gemini-cli-which-ai-coding-assistant-is-right-for-your-deployment-workflow

[^1_30]: https://amanhimself.dev/blog/first-few-days-with-codex-cli/

[^1_31]: https://northflank.com/blog/claude-code-vs-openai-codex

[^1_32]: https://www.deployhq.com/blog/getting-started-with-openai-codex-cli-ai-powered-code-generation-from-your-terminal

[^1_33]: https://learn.g2.com/open-ai-codex-cli

[^1_34]: https://www.reddit.com/r/codex/comments/1r49q5d/how_do_you_use_subagents_in_codex_cli/

[^1_35]: https://github.com/openai/codex/discussions/3898

[^1_36]: https://www.linkedin.com/posts/ravicaw_codex-aiagents-aicoding-activity-7416329555788869632--pbm

[^1_37]: https://developers.openai.com/codex/concepts/customization/

[^1_38]: https://opencode.ai/docs/agents/

[^1_39]: https://intuitionlabs.ai/articles/openai-codex-app-ai-coding-agents

[^1_40]: https://code.visualstudio.com/blogs/2026/02/05/multi-agent-development

[^1_41]: https://www.reddit.com/r/opencodeCLI/comments/1pbrc3m/built_an_open_source_app_to_run_multiple/

[^1_42]: https://www.reddit.com/r/opencodeCLI/comments/1qryge0/sandboxing_best_practices_discussion/

[^1_43]: https://www.reddit.com/r/opencodeCLI/comments/1r6wyqc/opencode_in_sandboxagent/

[^1_44]: https://openrouter.ai/docs/quickstart

[^1_45]: https://www.reddit.com/r/ClaudeCode/comments/1rht68z/how_i_run_long_tasks_with_claude_code_and_codex/


---

# but Codex CLI can run with custom openAI compatible endpoints like OpenRouter or OLLAMA? and can run with self hosted models like GLM 4.7 or 5 or Kimi K2.5?

it may be less optimized but these models are still useful and work well? search for real cases and people sharing their experience in 2026.

I lead a course for a bank, on the course we can use private ChatGPT Plus subscriptions, but in they work they will have to use self hosted models only. so I need tools that may work with them.

Security of the tool is also important, so even if OpenCode can run with any self hosted model it may not be the best option if security in the end-user's device will be lower and data may breach from the device if model follows e.g. prompt injection.

is Codex more suitable in that case? or Can we make OpenCode more secure?

Great set of questions - this is very practical for your bank course context. Let me give you the full picture.

## Codex CLI + Custom Endpoints: Does It Actually Work?

**Yes, but with a historically important caveat.** The original problem was that Codex CLI used OpenAI's `/v1/responses` endpoint (not `/v1/chat/completions`), while most compatible servers (Ollama, LM Studio, etc.) only spoke the Chat Completions API [^2_1]. This caused early frustration. **However, Ollama added official `/v1/responses` support**, and OpenRouter now has **first-class official documentation** for Codex CLI integration [^2_2]. This is confirmed working as of January-February 2026 [^2_3][^2_4].

The configuration in `~/.codex/config.toml` is straightforward [^2_2]:

```toml
model_provider = "openrouter"
model = "z-ai/glm-5.2"  # or any model on OpenRouter

[model_providers.openrouter]
name = "openrouter"
base_url = "https://openrouter.ai/api/v1"
env_key = "OPENROUTER_API_KEY"
```

For Ollama/self-hosted, you use the `oss` profile with `OPENAI_API_BASE` [^2_5]:

```toml
[profiles.selfhosted]
model_provider = "local"
model = "glm4:latest"

[model_providers.local]
base_url = "http://your-internal-server/v1"
api_key = "internal-key"
```


## GLM 4.7 / GLM 5 and Kimi K2 - Real 2026 Experiences

Real user data from the community as of late 2025/early 2026 [^2_6]:

- **GLM 4.7 / GLM 4.7:thinking**: Works reliably in agentic loops (95%+ of the time) after setting the router transformer to `openrouter` mode, which normalizes output formatting [^2_6]. (GLM-5.2 is the current generation - older 4.x benchmarks below may be outdated.)
- **Kimi K2**: Problematic. It frequently stops after 2-3 agentic steps, partly because angle brackets in code are misinterpreted as termination tokens, and partly because it adds conversational filler that breaks agent loops [^2_6]. Kimi K2 Thinking is even worse for autonomous use. This is a **real limitation for a course scenario** - students would be fighting the model, not learning the tool.
- **Minimax M2.1/M2.5**: Works cleanly without configuration changes [^2_6].
- **DeepSeek Coder / DeepSeek V3**: Widely reported to work well on Codex CLI with Ollama [^2_8].

The Reddit consensus [^2_6]: **GLM 4.7 is the best self-hosted option right now** for agentic coding workflows if you're not using OpenAI/Anthropic models.

## Your Bank Course Scenario - The Right Framework

This is a genuinely nuanced situation. You have two different audiences with two different constraints:


| Context | Students' Personal Setup | Work Setup |
| :-- | :-- | :-- |
| Model access | ChatGPT Plus (via OpenAI API) | Self-hosted only |
| Security sensitivity | Moderate | **High (bank-grade)** |
| Best tool | Codex CLI (OpenAI-native) | Either, but with hardening |

The real question is: **can the same tool serve both contexts?** Yes - Codex CLI with OpenRouter or `config.toml` profiles can switch between OpenAI and self-hosted seamlessly [^2_5][^2_2].

## Security: Codex CLI vs OpenCode for a Bank Environment

This is where **Codex CLI is clearly the safer default choice for enterprise/banking**. Here's why:

### Codex CLI Sandboxing Advantages

- Landlock (Linux) enforces filesystem isolation at the kernel level - even if a model follows a prompt injection attack, it **cannot read files outside the workspace** [^2_9][^2_10]
- Three explicit modes: `read-only`, `workspace-write`, `danger-full-access` - you can lock down to `workspace-write` for all bank deployments
- The Rust core means the sandbox enforcement is not bypassable via Node.js module tricks [^2_11]
- On Ubuntu specifically, Landlock requires no extra configuration - it's automatic at kernel level


### OpenCode Security Gaps

- No built-in sandbox - requires manual Docker setup or the `opencode-sandbox` npm plugin [^2_12][^2_13]
- Had an **unauthenticated RCE vulnerability** discovered in January 2026 [^2_14] - this is a serious red flag for banking environments
- Prompt injection via malicious code files could theoretically exfiltrate data to a model that "phones home" via tool calls if tool permissions are broad


### Can You Make OpenCode Secure Enough?

Yes, but it requires deliberate effort [^2_15][^2_13]:

1. **Run inside Docker** - the officially supported path for enterprise use [^2_15]
2. **Use `opencode-sandbox` plugin** with a strict `.opencode/sandbox.json` (whitelist filesystem paths, block network domains except your model endpoint)
3. **Use `--no-mcp`** flag to disable all MCP servers unless explicitly needed
4. **Apply Landlock manually** on Linux via bubblewrap (the plugin does this on Linux) [^2_13]

However, for students learning to use these tools in a bank context, **teaching correct security posture is itself part of the lesson**. Codex CLI's security model is declarative and harder to accidentally misconfigure.

## Recommendation for Your Course

For the **bank training scenario**, structure it this way:

- **During course (ChatGPT Plus)**: Use Codex CLI with the standard OpenAI config - students get the best model quality and the full feature set without friction
- **For the "at work" module**: Switch to a Codex CLI `config.toml` profile pointing at the bank's internal OpenAI-compatible endpoint running **GLM 4.7 or GLM 5** - the most reliable self-hosted model for agentic loops [^2_6]
- **Security layer**: Always run with `--sandbox workspace-write` on Linux. On Windows (which some bank workstations will be), push for Docker + WSL2 since native Windows sandboxing in Codex is still experimental [^2_9]
- **Prompt injection defense**: Teach the AGENTS.md pattern to define strict system boundaries, and use approval mode (`--approval-mode`) so the model asks before executing any shell command [^2_16][^2_17]

OpenCode is more model-flexible but the January 2026 RCE vulnerability and lack of native sandboxing make it a harder sell in a compliance-conscious banking environment without extra DevOps overhead [^2_14][^2_18].
<span style="display:none">[^2_19][^2_20][^2_21][^2_22][^2_23][^2_24][^2_25][^2_26][^2_27][^2_28][^2_29][^2_30][^2_31][^2_32][^2_33][^2_34]</span>

<div align="center">⁂</div>

[^2_1]: https://github.com/ollama/ollama/issues/10309

[^2_2]: https://openrouter.ai/docs/guides/guides/coding-agents/codex-cli

[^2_3]: https://ollama.com/blog/codex

[^2_4]: https://www.linkedin.com/posts/exploring-artificial-intelligence_how-to-run-codex-cli-locally-with-ollama-activity-7423753249096142849-d8fa

[^2_5]: https://inventivehq.com/knowledge-base/openai/how-to-use-local-models

[^2_6]: https://www.reddit.com/r/LocalLLaMA/comments/1pxbgyf/how_to_get_sota_opensource_models_glm_47_kimi_k2/

[^2_7]: https://www.nxcode.io/resources/news/glm-5-open-source-744b-model-complete-guide-2026

[^2_8]: https://dev.to/shashikant86/codex-cli-running-gpt-oss-and-local-coding-models-with-ollama-lm-studio-and-mlx-403g

[^2_9]: https://fossies.org/linux/codex-rust/codex-rs/core/src/sandboxing/mod.rs

[^2_10]: https://fossies.org/linux/codex-rust/codex-rs/core/src/safety.rs

[^2_11]: https://github.com/openai/codex/blob/main/codex-rs/README.md

[^2_12]: https://www.reddit.com/r/opencodeCLI/comments/1riizl1/sandboxed_opencode/

[^2_13]: https://libraries.io/npm/opencode-sandbox

[^2_14]: https://news.ycombinator.com/item?id=46581095

[^2_15]: https://docs.docker.com/ai/sandboxes/agents/opencode/

[^2_16]: https://es.vectra.ai/topics/prompt-injection

[^2_17]: https://appsecsanta.com/ai-security-tools/prompt-injection-guide

[^2_18]: https://www.reddit.com/r/opencodeCLI/comments/1rgmh3t/do_you_run_opencode_in_a_sandboxed_environment_or/

[^2_19]: https://github.com/openai/codex/issues/26

[^2_20]: https://docs.ollama.com/integrations/codex

[^2_21]: https://github.com/cybozu/prompt-hardener

[^2_22]: https://www.youtube.com/watch?v=hC72A_1J5Co

[^2_23]: https://www.radware.com/cyberpedia/prompt-injection/

[^2_24]: https://github.com/ymichael/open-codex/issues/4

[^2_25]: https://ollama.com/blog/openai-compatibility

[^2_26]: https://blog.patshead.com/2026/01/squeezing-value-from-free-and-low-cost-ai-coding-subscriptions.html

[^2_27]: https://github.com/openai/codex/issues/8240

[^2_28]: https://broadchannel.org/prompt-injection-defense-llm-security/

[^2_29]: https://www.reddit.com/r/LocalLLaMA/comments/1o1e3st/using_ollama_codex_cli_seems_very_under_powered/

[^2_30]: https://youtrack.jetbrains.com/projects/LLM/issues/LLM-23964/Unable-to-add-custom-model-from-custom-Open-AI-endpoint-to-Codex-integration-in-JetBrain-AI

[^2_31]: https://news.ycombinator.com/item?id=43754620

[^2_32]: https://zeabur.com/blogs/use-codex-with-ai-hub

[^2_33]: https://ja.vectra.ai/topics/prompt-injection

[^2_34]: https://www.reddit.com/r/ClaudeCode/comments/1n6u89m/tried_codex_after_all_the_noise_here_and_im/


---

# does it make sense to use both wsl2 and docker? why? WSL with eg Ubuntu is already some kind of isolated container. Is it enough?

and how to use both? I know Docker Desktop on Windows has new experimental Agent Sanbox features, but does it make sense with WSL2 and Codex CLI sandbox inside Ubuntu WSL? how to make it work together, both WSL and docker? docker server inside WSL? but then we don't have these new docker features like credentials injection that are only on desktop version.

This is a great architectural question and the answer matters a lot for your bank course. Let me break down the real isolation model of each layer clearly.

## WSL2 Is NOT a Real Sandbox

This is the most important misconception to clear up. WSL2 is a **lightweight Hyper-V VM**, not a container, and it has several fundamental isolation gaps [^3_1][^3_2]:

- **Windows can read WSL2 filesystem directly** via `\\wsl$\Ubuntu\...` from any Windows process - no permission required
- **All WSL2 distros share a single Linux kernel instance** - one distro can modify kernel parameters that affect all others [^3_1]
- **Users can access the Docker-Desktop WSL distro directly** via `wsl -d docker-desktop`, bypassing all Docker Desktop security settings [^3_1]
- There is no wall between your Ubuntu WSL2 env and the Windows host at the filesystem level

So WSL2 Ubuntu gives you a **Linux environment**, not a **security boundary**. Critically though - **Codex CLI's Landlock sandbox still works and has real value inside WSL2**, because it restricts what the Codex process can access *within Linux*, regardless of the WSL2 host boundary. It just doesn't protect WSL2 from Windows.

## The Docker-in-WSL2 Topology - Three Distinct Scenarios

```
┌─────────────────────────────────────────────────────────┐
│                    WINDOWS HOST                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │               WSL2 VM (shared kernel)              │ │
│  │  ┌──────────────┐  ┌──────────────────────────┐   │ │
│  │  │ Ubuntu distro│  │  docker-desktop distro   │   │ │
│  │  │  Codex CLI   │  │   Docker Engine          │   │ │
│  │  │  + Landlock  │  │   + containers           │   │ │
│  │  └──────────────┘  └──────────────────────────┘   │ │
│  └────────────────────────────────────────────────────┘ │
│         ↑ \\wsl$\ path: Windows reads ALL of above      │
└─────────────────────────────────────────────────────────┘
```


### Scenario A: WSL2 Ubuntu + Codex CLI Landlock only (no Docker)

- ✅ Codex CLI Landlock blocks the AI agent from touching files outside the workspace (kernel-enforced)
- ✅ No Docker complexity, runs fast, easy for course attendees
- ❌ Windows host can still read/write WSL2 files
- ❌ No network isolation - malicious model output could exfiltrate data via shell commands unless `--no-network` is also set
- **Best for**: course environment, students learning the tool, non-critical projects


### Scenario B: Docker Engine installed directly inside WSL2 Ubuntu (no Docker Desktop)

You install `docker-ce` inside your Ubuntu distro directly [^3_3]:

```bash
curl -fsSL https://get.docker.com | sh
```

```bash
sudo usermod -aG docker $USER
```

Then run Codex CLI inside a Docker container:

- ✅ Real container filesystem isolation on top of Landlock
- ✅ No Docker Desktop license requirement (relevant for banks - Docker Desktop requires a paid license for companies >250 employees)
- ✅ Network namespace isolation per container
- ❌ **No Docker Desktop Agent Sandbox features** (no credential injection proxy, no ECI, no Settings Management)
- ❌ Containers still share the WSL2 kernel with the host Ubuntu distro
- **Best for**: Dev teams that want layered isolation without Docker Desktop overhead


### Scenario C: Docker Desktop (WSL2 backend) + Agent Sandbox

Docker Desktop runs its own `docker-desktop` WSL2 distro. Agent Sandbox works here [^3_4]:

- ✅ Credential injection proxy - your API keys are intercepted and injected transparently, never stored in container env [^3_4]
- ✅ `opencode` and Codex CLI both have official Docker sandbox templates [^3_5][^3_4]
- ⚠️ Enhanced Container Isolation (ECI) is **weaker on WSL2 backend** than Hyper-V [^3_1] - users can access `docker-desktop` distro directly and bypass security settings
- ❌ CVE-2025-9074 (patched in 4.44.3) was specifically a WSL2 shared-kernel attack vector [^3_6][^3_7]
- **Requires Docker Desktop ≥ 4.44.3** to be safe


### Scenario D: Docker Desktop (Hyper-V backend) + ECI <- Maximum security

| Security feature | WSL2 backend | Hyper-V backend |
| :-- | :-- | :-- |
| Strongly secure containers | ✅ | ✅ |
| VM protected from user direct access | ❌ | ✅ |
| Dedicated kernel per VM | ❌ | ✅ |
| Agent Sandbox / credential injection | ✅ | ✅ |
| ECI full enforcement | Partial | ✅ Full |

Docker official recommendation: **use Hyper-V for maximum security** [^3_1]. ECI on Hyper-V means even if the AI model follows a prompt injection and tries to escape the container, it hits a dedicated kernel boundary, not the shared WSL2 kernel. This is the architecture you'd want for a real bank deployment.

The tradeoff is performance - Hyper-V mode is slower for file I/O than WSL2 backend - but for a coding agent that's bottlenecked by LLM latency anyway, it barely matters.

## The Credential Injection Feature - Is It Worth It?

Docker Agent Sandbox's credential proxy is genuinely useful in a bank scenario [^3_4]: API keys are set as environment variables in your shell config, and the sandbox proxy **intercepts all API calls and injects credentials transparently**. This means:

- The Codex CLI process never holds the raw API key in memory
- Containers can't exfiltrate the key via env vars (`docker inspect` won't show it)
- Useful for a shared training machine where you don't want students seeing each other's keys

However, this feature requires **Docker Desktop** (not Docker Engine inside WSL). If your bank has a Docker Desktop enterprise license, use Scenario D (Hyper-V + ECI + Agent Sandbox). If not, Scenario B (Docker Engine in WSL2) is the practical alternative.

## Practical Recommendation for Your Course

For the **training machines during the course**:

- **Scenario A** (WSL2 + Codex CLI `--sandbox workspace-write`) is enough - it's simple, fast, and teaches the right patterns without fighting Docker complexity
- Add `--no-network` or use an approval policy for shell commands to prevent network exfiltration

For the **"this is how you'd deploy it at the bank" demo**:

- Show Scenario D on one machine to illustrate the full security stack
- Key point to teach: **depth of defense** - Codex Landlock + Docker container + Hyper-V VM isolation are three independent layers, any one of which would stop most AI agent escape scenarios
- WSL2 alone is *not* a security boundary vs. the Windows host, but it IS a Linux environment where real kernel-level security tools (Landlock, namespaces, seccomp) work correctly [^3_8]
<span style="display:none">[^3_10][^3_11][^3_12][^3_13][^3_14][^3_15][^3_16][^3_9]</span>

<div align="center">⁂</div>

[^3_1]: https://docs.docker.com/enterprise/security/hardened-desktop/enhanced-container-isolation/limitations/

[^3_2]: https://docs.docker.com/desktop/features/wsl/

[^3_3]: https://oneuptime.com/blog/post/2026-01-16-docker-wsl2-windows/view

[^3_4]: https://docs.docker.com/ai/sandboxes/agents/docker-agent/

[^3_5]: https://docs.docker.com/ai/sandboxes/agents/opencode/

[^3_6]: https://www.mindpatch.net/posts/docker-escape-ssrf/

[^3_7]: https://isosecu.com/blog/windows-cve-2025-9074-docker-ssrf

[^3_8]: https://zaclohrenz.com/posts/2025/september13/

[^3_9]: https://learn.microsoft.com/en-us/defender-endpoint/mde-plugin-wsl

[^3_10]: https://stackoverflow.com/questions/61920866/difference-between-wsl2docker-desktop-windows-and-directly-install-docker-on

[^3_11]: https://www.reddit.com/r/wsl2/comments/1ixzdxu/is_wsl2_still_slow_in_2025/

[^3_12]: https://forums.docker.com/t/difference-between-docker-desktop-and-docker-engine/124612

[^3_13]: https://learn.microsoft.com/en-us/windows/wsl/troubleshooting

[^3_14]: https://www.reddit.com/r/docker/comments/u3bw5a/docker_desktop_vs_docker_within_wsl2/

[^3_15]: https://github.com/microsoft/WSL/discussions/14261

[^3_16]: https://forums.docker.com/t/docker-credential-desktop-exe-executable-file-not-found-in-path-using-wsl2/100225


---

# as training VMs we have Windows Server 2022 where Docker Desktop is not supported.

do you think as main course env just codex with sandbox directly on Windows in either power shell or git bash should be enough? for most of the course material? But Bash will provide more binaries that agents sometimes try to use, so maybe safer? I also plan to show Codex Desktop app which shares configs and sessions with both local codex cli and cloud sessions. it won't work inside WSL, and would not share sessions with WSL Codex clu, yes?

or should I use codex cli inside WSL most of the time with codex sandbox only? is it better for agents to run vs git bash? less risky?

Ideally I would like to show them also the most secure scenario so with Docked Desktop and codex CLI inside it using its own sanboxing. but I can't do this on VMs, so I probably only can show it on my local windows and explain it shortly without exercises? I don't know if they have a licence either way.

This has very practical implications for the course design. Let me give you a clear, honest breakdown.

## Docker Desktop on Windows Server 2022

Confirmed: **fully unsupported, full stop** [^4_1][^4_2][^4_3]. Not a licensing issue - it's architecturally not compatible with Windows Server editions at all. Docker Engine (CE/Moby) can be installed on Server 2022, but you lose every advanced feature you were considering: no ECI, no Agent Sandbox, no credential injection proxy. For your course, Docker is off the table.

## Native Windows Sandbox - It's Actually Real and Sufficient

This is the good news: Codex CLI has a **proper native Windows sandbox** that doesn't require WSL or Docker at all [^4_4]. It has two modes, configured in `config.toml`:

```toml
[windows]
sandbox = "elevated"   # or "unelevated"
```

**Elevated mode** gives you:

- **Restricted Token**: Codex runs as a dedicated sandbox user with stripped privileges [^4_4]
- **Filesystem ACLs**: writes blocked outside the working directory
- **Windows Firewall rules**: network access blocked by default, requires explicit approval [^4_4]

This is meaningful isolation for a course - the agent genuinely cannot reach outside the project folder. It's not Landlock-grade kernel enforcement, but for training scenarios it's entirely adequate.

## PowerShell vs Git Bash - This Is a Real Problem

This is not just a comfort question - there's a documented functional issue. Codex agents running on Windows **consistently misbehave in PowerShell**: they generate bash-style commands, fail, then spiral into trying random PS equivalents or Python workarounds [^4_5]. The community workaround is installing Git Bash and telling the agent to use bash explicitly [^4_5]:

```
"Please use bash, do not use powershell"
```

However, there's a tension here:

- **Git Bash** gives the agent familiar Unix tools (grep, sed, awk, curl, find) and makes tasks run smoothly
- **Windows Sandbox integration** is tested and most reliable from native Windows Terminal / PowerShell context
- **Git Bash + sandbox** can work, but sandbox enforcement is technically a Windows-native construct sitting beneath the shell layer - it's still active regardless of which shell is on top

**Recommendation for course**: Use Windows Terminal with Git Bash profile, with `sandbox = "elevated"` in config. The sandbox operates at the process/ACL level, not the shell level, so it protects you regardless of which shell is used.

## Codex Desktop App + WSL - Session Sharing Problem

You correctly identified this issue. Here's the real situation [^4_6][^4_7]:

- The Codex Desktop app is a **Windows native application** - it cannot run inside WSL
- It connects to Codex CLI via a **local loopback bridge** (`127.0.0.1:PORT`) - this works when CLI is running on Windows natively
- When Codex CLI runs inside WSL2, the loopback is **not the same loopback** - WSL2 has its own network namespace with a virtual IP, and the Desktop app polling `127.0.0.1` won't find the WSL2 process [^4_6]
- Config (`config.toml`) lives at `C:\Users\<user>\.codex\config.toml` for Windows/Desktop, and at `~/.codex/config.toml` in WSL - **two separate configs**, not synced
- Session history is also stored separately

The workaround (from community) is to install Codex on Windows natively, then configure the Desktop app to *invoke* WSL as the execution backend - but this is fiddly and not the happy path [^4_7].

## Course Architecture - Practical Design

Given all constraints (Windows Server 2022, no Docker Desktop, mixed use of Desktop app), here's what I'd structure:

**Module 1-3: Core workflows** -> Codex CLI natively on Windows, Windows Terminal + Git Bash, `sandbox = "elevated"`. Simple to set up, works reliably, sandbox is real. Students get the right mental model of approval policies and sandbox limits.

**Module 4: Codex Desktop App** -> Run on Windows natively (same machine), same `config.toml`. Sessions and context flow between Desktop app and native CLI here because both are on the Windows path. **This breaks if you switch to WSL during the same session** - teach this boundary explicitly.

**Module 5: WSL2 + Landlock (Linux-grade sandbox)** -> Separate module where WSL2 is the environment. Explain clearly this is a different isolated context with a stronger sandbox (kernel Landlock vs Windows ACLs), but no Desktop app integration. Ideal for showing the more advanced Linux-native security story.

**Module 6 (demo-only on your laptop)**: Docker Desktop + ECI + Agent Sandbox on Windows 11/macOS. No hands-on exercises, just a live demo showing credential injection and Hyper-V container escape prevention. Since students can't reproduce it on their VMs, frame it as "this is the production-grade bank deployment model to advocate for with your IT team."


| Environment | Sandbox quality | Desktop App sync | Git Bash works | On WS2022 VMs |
| :-- | :-- | :-- | :-- | :-- |
| Windows native + elevated | ✅ Good | ✅ Yes | ✅ Yes | ✅ Yes |
| WSL2 + Landlock | ✅✅ Best | ❌ No | ✅ Native bash | ✅ Yes |
| Docker Desktop + ECI | ✅✅✅ Max | ⚠️ Complex | ✅ Yes | ❌ No |

The **key teaching moment** worth building a slide around: security is layered, and each environment trades off some capability for some protection. For developers at the bank, the answer is WSL2 (Linux Landlock) for autonomous agent tasks, and native Windows + elevated sandbox for interactive sessions where they want Desktop app continuity.
<span style="display:none">[^4_10][^4_11][^4_12][^4_13][^4_14][^4_15][^4_16][^4_8][^4_9]</span>

<div align="center">⁂</div>

[^4_1]: https://www.reddit.com/r/docker/comments/1dh571r/running_docker_containers_on_windows_server_2022/

[^4_2]: https://forums.docker.com/t/issue-installing-docker-desktop-on-windows-server-2022-wsl-2/123009

[^4_3]: https://forums.docker.com/t/docker-desktop-on-windows-server-2022-configuration-and-data-isolation-between-domain-users/150332

[^4_4]: https://developers.openai.com/codex/cli/features/

[^4_5]: https://github.com/openai/codex/issues/2549

[^4_6]: https://github.com/openai/codex/issues/2744

[^4_7]: https://www.reddit.com/r/codex/comments/1rnxh01/codex_app_in_wsl/

[^4_8]: https://forums.docker.com/t/unable-to-run-docker-desktop-as-service-on-windows-server-2022/138022

[^4_9]: https://forums.docker.com/t/supported-install-procedure-for-windows-server-2022-without-internet-access/136111

[^4_10]: https://www.reddit.com/r/docker/comments/1l1rlh5/windows_server_2022_installation_issues/

[^4_11]: https://developers.openai.com/codex/windows/

[^4_12]: https://www.reddit.com/r/codex/comments/1qyeyaf/codex_in_windows_wsl_or_not/

[^4_13]: https://github.com/openai/codex/discussions/341

[^4_14]: https://forum.edgeimpulse.com/t/unable-to-use-docker-build-on-windows-server-2022/5958

[^4_15]: https://developers.openai.com/codex/cli/reference/

[^4_16]: https://www.youtube.com/watch?v=laM6xjEGMiE


---

# does Claude Code also support other models? I know it is possible to override the API enddpoint and use OpenRouter or Z.ai compatible endpoints, so we can use this tool with different models than Claude?

but search for opinions and use cases how good it works with different models? and can we use Claude Code Desktop with different endpoint too or is it only based on Claude subscription and doesn't work with custom env variables with custom endpoints and APIs keys?

does it support self hosted models with eg Ollama? does Ollama have compatible endpoint?

Great set of questions, and the January 2026 Ollama announcement changes the picture significantly. Here's everything you need to know.

## The Core Mechanism: `ANTHROPIC_BASE_URL`

Claude Code supports a fully undocumented-but-working override via environment variables [^5_1]:

```bash
export ANTHROPIC_BASE_URL="https://openrouter.ai/api/v1"
```

```bash
export ANTHROPIC_AUTH_TOKEN="your-openrouter-key"
```

```bash
export ANTHROPIC_MODEL="openai/gpt-oss-20b"
```

This works because Claude Code uses the Anthropic Messages API format, and any proxy that translates between OpenAI/Anthropic formats can sit in the middle [^5_2]. OpenRouter explicitly documents this for Claude Code now [^5_3]. The key limitation is that Claude Code sends requests formatted as Claude API calls - so the endpoint **must speak Anthropic Messages API format**, not just OpenAI Chat Completions.

## Ollama - Yes, Now Officially Compatible

In **January 2026, Ollama added native support for the Anthropic Messages API** [^5_4][^5_5]. This is the key unlock - previously you needed a proxy. Now you just point Claude Code directly:

```bash
export ANTHROPIC_BASE_URL="http://localhost:11434"
```

```bash
export ANTHROPIC_AUTH_TOKEN="ollama"
```

```bash
export ANTHROPIC_MODEL="glm4:latest"
```

Docker Model Runner also exposes an Anthropic-compatible API and works the same way [^5_5]. These are confirmed working setups as of early 2026.

## Real-World Quality: Honest Community Feedback (2026)

This is where it gets honest - and for your bank course context, this matters a lot:

**Models that work reasonably well in Claude Code:**

- **GLM 5 / GLM 4.7** - users in March 2026 report GLM 5 matching or exceeding Claude Opus 4.6 on several benchmarks [^5_6][^5_7]. One user: *"Today I find GLM 5 to be better than Codex 5.3-Medium in quality of output and thoroughness"* [^5_6]. GLM 4.7 reliably completes agentic loops [^5_8]
- **Qwen3-Coder** - strong coding performance, widely used via OpenRouter free tier [^5_9][^5_10]
- **DeepSeek V3** - great for architecture/planning, slightly weaker for agentic execution [^5_11]
- **MiniMax M2.1** - *"almost as good as Claude Code, runs at ~30 tokens/sec with 160GB VRAM"* [^5_12]; also works locally but requires significant prompting guidance [^5_13]
- **Kimi K2 via OpenRouter** - *"speedy and effective but doesn't match Opus/Sonnet"* [^5_13] - however known agentic loop issues as discussed earlier

**What consistently degrades without Claude:**

- Multi-step autonomous task completion (models stop mid-task or go off-track)
- Complex refactoring across many files simultaneously
- The precise instruction-following that makes Claude Code's tool use so reliable
- Community consensus [^5_14]: *"the reason Claude Code works so well is partially the model (current `opus` alias / Opus 4.8) AND the harness - removing either degrades quality"*

The honest framing for your students: **these models work for learning the tool**, but in production the gap to Claude is real and meaningful.

## The Proxy Approach for Flexibility: Claude Code Router

For switching between multiple models without changing env vars, **Claude Code Router (CCR)** is the most practical tool [^5_2][^5_10]. It runs a local proxy that intercepts Claude API calls and routes to any backend:

```json
{
  "Providers": [
    {
      "name": "openrouter",
      "api_base_url": "https://openrouter.ai/api/v1/chat/completions",
      "api_key": "${OPENROUTER_API_KEY}",
      "models": ["qwen/qwen3-coder:free", "openai/gpt-oss-20b:free"]
    },
    {
      "name": "ollama",
      "api_base_url": "http://localhost:11434/v1/chat/completions",
      "api_key": "ollama",
      "models": ["glm4:latest", "deepseek-coder:6.7b"]
    }
  ]
}
```

Then: `export ANTHROPIC_BASE_URL="http://localhost:9090"` [^5_10]. This is useful for course demos where you want to switch models live without restarting the session.

For **enterprise/bank use** there's also **LiteLLM** as a centrally managed proxy - more ops overhead but gives you one endpoint that the whole team points at, with model aliasing, logging, and rate limiting [^5_15].

## Claude Code Desktop App + Custom Endpoints

The Desktop app (the ChatGPT/Cursor-style interface) reads from the **same environment variables** as the CLI - `ANTHROPIC_BASE_URL` set in your shell profile or `.env` applies to both [^5_5][^5_1]. It is NOT hardcoded to only Anthropic subscriptions. However:

- It still uses the **Anthropic Messages API schema** internally - so the endpoint still needs to speak that format or proxy it
- OpenRouter works confirmed [^5_16]
- Azure AI Foundry has **first-class official support** via `CLAUDE_CODE_USE_FOUNDRY=1` + `ANTHROPIC_FOUNDRY_RESOURCE` - this is likely the most relevant for a bank that has Azure enterprise agreements [^5_17]:

```bash
export CLAUDE_CODE_USE_FOUNDRY=1
```

```bash
export ANTHROPIC_FOUNDRY_RESOURCE=your-azure-resource-name
```

This is worth a dedicated slide in your course - many banks already have Azure AI Foundry access and wouldn't need to set up a separate Ollama server at all.

## For Your Bank Course: Model Strategy

| Scenario | Tool Config | Best Model Option |
| :-- | :-- | :-- |
| During course (ChatGPT Plus) | `ANTHROPIC_BASE_URL` = Anthropic default | subscription default model |
| At work, Azure available | `CLAUDE_CODE_USE_FOUNDRY=1` | Claude via Azure Foundry (bank's contract) |
| At work, fully air-gapped | Ollama + Anthropic-compatible API | GLM 5 or Qwen3-Coder self-hosted |
| Learning/testing budget | OpenRouter CCR proxy | Qwen3-Coder:free or GPT-OSS-20b:free |

The Azure Foundry path [^5_17] is the most credible "here's how your bank would deploy this" story - it keeps data in the bank's Azure tenant, uses existing enterprise agreements, and doesn't require IT to approve a new vendor. That might be the strongest practical takeaway for your banking audience.
<span style="display:none">[^5_18][^5_19][^5_20][^5_21][^5_22][^5_23][^5_24][^5_25][^5_26][^5_27][^5_28]</span>

<div align="center">⁂</div>

[^5_1]: https://github.com/anthropics/claude-code/issues/216

[^5_2]: https://naresh.se/en/posts/2026/2026-01-22_claude_code_with_openai/

[^5_3]: https://openrouter.ai/docs/guides/guides/coding-agents/claude-code-integration

[^5_4]: https://www.linkedin.com/pulse/claude-code-open-source-models-using-ollama-guzey-bufjc

[^5_5]: https://www.docker.com/blog/run-claude-code-locally-docker-model-runner/

[^5_6]: https://www.reddit.com/r/LocalLLaMA/comments/1r5beqe/the_current_top_4_models_on_openrouter_are_all/

[^5_7]: https://o-mega.ai/articles/open-source-personal-ai-build-your-own-agent-2026

[^5_8]: https://www.reddit.com/r/LocalLLaMA/comments/1pxbgyf/how_to_get_sota_opensource_models_glm_47_kimi_k2/

[^5_9]: https://github.com/ruvnet/claude-flow/wiki/Using-Claude-Code-with-Open-Models

[^5_10]: https://lgallardo.com/2025/08/20/claude-code-router-openrouter-beyond-anthropic/

[^5_11]: https://www.reddit.com/r/ChatGPTCoding/comments/1iekf4l/the_most_used_model_on_openrouter_by_far_is/

[^5_12]: https://www.reddit.com/r/LocalLLaMA/comments/1q82ae8/start_of_2026_whats_the_best_open_coding_model/

[^5_13]: https://www.reddit.com/r/LocalLLaMA/comments/1ro072s/how_many_of_you_using_local_or_openrouter_models/

[^5_14]: https://www.reddit.com/r/ClaudeCode/comments/1qkgqxr/oc_used_claudecode_with_different_models_via/

[^5_15]: https://www.reddit.com/r/ClaudeAI/comments/1l88015/how_to_set_custom_base_url_in_claude_code_like/

[^5_16]: https://www.youtube.com/watch?v=GRUjApPqCoE

[^5_17]: https://learn.microsoft.com/en-us/azure/foundry/foundry-models/how-to/configure-claude-code?view=foundry\&tabs=bash

[^5_18]: https://github.com/ruvnet/ruflo/wiki/Using-Claude-Code-with-Open-Models

[^5_19]: https://www.youtube.com/watch?v=N7CQdYaeUEE

[^5_20]: https://www.reddit.com/r/ClaudeAI/comments/1mi5l9m/routing_claude_code_subagents_to_openai_models/

[^5_21]: https://github.com/zed-industries/zed/discussions/37842

[^5_22]: https://www.youtube.com/watch?v=ypaNNpi61Bw

[^5_23]: https://createaiagent.net/self-hosted-llm/

[^5_24]: https://www.reddit.com/r/openrouter/comments/1q5axc9/please_recommend_the_best_coding_models_based_on/

[^5_25]: https://www.linkedin.com/posts/curtburk_aideveloper-localai-poweredbycoffee-activity-7433935870468108288-A3v7

[^5_26]: https://www.reddit.com/r/FlutterDev/comments/1r5ldbn/which_models_works_best_in_your_experience/

[^5_27]: https://www.reddit.com/r/vibecoding/comments/1reeqmc/best_budgetfriendly_ai_ides_and_clis_in_2026/

[^5_28]: https://www.youtube.com/watch?v=74pdg4IuRi8


---

# this bank don't want to use any cloud. only self hosted tools and models. so no azure foundry.

I plan to focus on Codex with OpenAI licences as the base because it will let use use more tokens within participants subscription plans and will work best for learning best ways to use agents with sub agents and long running tasks that burns tokens very fast.

as a 2nd option I plan to show them also how to configure Codex CLI and maybe also Codex App (if possible) with Ollama or open router to demonstrate how they can connect with self hosted models later with they real work.

and and 2nd option I plan to show them Claude Code CLI and Desktop as alternative, with open router also to demonstrate how they can work with it in they work env. and to show it as alternative tool that had its own pros and cons and sometimes works better than codex because has different philosophy to harnesses (bash-first vs RPC tools) and sandboxing (no sandbox by default with optional full Linux VM for Claude desktop app vs default sandbox in codex all the time). but we will only show the differences and how to use it without making full project on it to safe tokens on my OpenRouter and let them use codex with their subscription most of the time.

I will not show OpenCode to don't introduce too many tools and to focus on workflows and skills not the tools.

some of them also use JetBrains IntelliJ but without any AI models and plugins because they can't use external calls in their bank. so I consider showing the AI assistant inside IntelliJ but since they won't be able to use it at they work either way I consider if it makes sense to show it at all? is it possible to override jetbrains AI assistant with custom endpoint and own models? I know there is Junie agent but also they have Claude Code integration based in Claude SDK directly and Codex integration based also on custom SDK, so these integrations doesn't use CLI agents with ACP protocol so not sure if we can override endpoints for them and use self hosted models?

it also supports ACP catalog of agents and we can use e.g. OpenCode or Gemini CLI as ACP, but I don't see option to use ClaudeCode and Codex as ACP. is that true? can you search and confirm?

they can take free trial on these VMs to use credits from jetbrains but since they won't be able to use it at work and from my experience these tools works much worse than agents from Codex or Claude code CLI directly, not sure if it makes sense to show them at all? maybe I will only tell the difference, explain that CLI tools and desktop apps from codex and Claude are much better and provide much more functionality and we will not use AI assistant inside IntelliJ? they can use it for checking code and commuting or starting the project if they like it, because the demo app we will build during the course will be in Java Spring AI backend with React or Angular frontend, but we will use agents outside IntelliJ all the time (in IntelliJ build in terminal if they prefer, but I installed and configured WezTerm on VMs which is better to TUI and both codex and Claude CLI, so AI will recommend it).

one person also prefer VSCode so imho it doesn't matter so much which IDE they use if we use external agents all the time either way?

what do you think about this plan? validate my information about IntelliJ AI assistant

This is an excellent course design - the logic is solid and the trade-offs you're making are the right ones. Let me validate everything and correct a couple of important details about the ACP/IntelliJ picture.

## Your Course Plan - Validated ✅

The structure you outlined is well thought out. The key insight - **use Codex+OpenAI subscriptions for the real learning, use OpenRouter/Ollama only for "this is how your work setup will look"** - is exactly right pedagogically. Students burn tokens learning agentic patterns, not fighting model quality degradation. The "show Claude Code as an alternative philosophy" module is also genuinely valuable because the bash-first vs RPC tool model is a conceptual difference worth understanding, not just a UI preference.

Dropping OpenCode was the right call. Three CLI agents would confuse the message.

## JetBrains AI Assistant - Custom Endpoints: YES, Natively Supported

Your intuition was approximately right but the actual support is **better than you thought**. As of the current official docs (March 2026), JetBrains AI Assistant natively supports [^6_1][^6_2]:

- **Ollama** (direct integration at `localhost:11434`, no extra config) [^6_2]
- **LM Studio** (OpenAI-compatible endpoint)
- **Any OpenAI-compatible endpoint** (LiteLLM, custom internal servers) [^6_1]
- **Anthropic Claude** directly

No proxy needed, no hacks - it's in Settings -> Third-party AI Providers, select provider, paste URL, Test Connection [^6_1]. So if the bank deploys a GLM 5 server internally, AI Assistant *can* talk to it. **But the real constraint remains network policy** - if the IDE can't reach the internal model server, that's an IT firewall issue, not a JetBrains limitation.

## Historical claim, superseded 5.11.2026: Codex and Claude Code in JetBrains - NOT ACP Agents

This is the important correction. You were right to be suspicious. Here's the exact picture [^6_3][^6_4][^6_5]:

**ACP Registry agents (January 2026 launch)** - available as ACP agents inside JetBrains IDEs [^6_4]:


| Agent in ACP Registry | Notes |
| :-- | :-- |
| OpenCode | ✅ Full ACP, can use Ollama models via config [^6_6] |
| Gemini CLI | ✅ Native ACP |
| GitHub Copilot | ✅ via ACP |
| Qwen Code | ✅ via ACP |
| Auggie CLI | ✅ via ACP |
| Mistral Vibe | ✅ via ACP |
| **Codex CLI** | Historical claim superseded 5.11.2026: Codex is available through the current ACP Registry integration; see correction above. |
| **Claude Code** | ❌ NOT in ACP Registry |

Codex and Claude Code are integrated via **direct proprietary SDK integrations**, not ACP [^6_3][^6_5]. This has a specific consequence: Zed had to build a custom wrapper for Claude Code because it *doesn't speak ACP natively*, and a separate adapter for Codex [^6_3]. JetBrains did the same - the Codex integration uses the OpenAI Codex SDK directly, which is why [^6_7] there are known issues trying to redirect it to custom OpenAI-compatible endpoints (it works only for the official OpenAI Codex endpoint). The Claude Code integration in JetBrains Air calls the Anthropic SDK directly [^6_8].

So to be precise about the custom endpoint question for Junie/Air specifically: **the native Codex panel inside JetBrains routes to OpenAI only**, and the Claude Agent routes to Anthropic only. You cannot substitute a self-hosted model in those specific panels. The generic AI Assistant chat (third-party providers) is a separate system where Ollama/custom endpoints *do* work - but that's just an inline chat, not an autonomous agent loop.

## Should You Show IntelliJ AI at All?

Your instinct to skip deep coverage is correct. Here's the clearest framing for your decision:

**Arguments for a brief mention only (5-10 min):**

- Participants genuinely cannot use external model calls at work, so even the best JetBrains integration is blocked at the firewall
- The agent quality inside the IDE panel is measurably weaker than CLI-native agents - JetBrains itself admits this indirectly by saying "not everything their SDK offers is available via ACP" [^6_3]
- IDEs abstract away the tool calls and sandbox behavior which are core to what you're teaching
- WezTerm being pre-installed on the VMs is actually the right call - Codex and Claude Code's TUI rendering (colors, streaming, diff views) is designed for proper terminal emulators

**What the brief mention should cover:**

- Show the ACP registry exists so they know external CLI agents *can* appear inside IntelliJ
- Show that AI Assistant CAN be pointed at a self-hosted Ollama server (for when IT eventually opens that network path)
- Explain that the Codex and Claude integrations in JetBrains are SDK-native and OpenAI/Anthropic-only, so they'd need the CLI anyway for self-hosted model work
- Frame it as: *"the terminal agents we've been learning are intentionally more powerful than what fits inside an IDE panel"*

Since participants are building a **Java Spring AI backend + React/Angular frontend**, the most compelling JetBrains-relevant point is actually the **Java compilation/build feedback loop** - running `mvn test` or Gradle from inside IntelliJ vs running it from the agent's bash tools. That's a real workflow decision worth 5 minutes of discussion: sometimes IDE build integration beats what an agent can see.

## On the IDE Question (VSCode vs IntelliJ)

You're exactly right that it doesn't matter much when the AI is an external agent. The IDE becomes a file viewer and git client. The one real exception is **language-server features** (Java type inference, Spring Boot auto-complete, Angular service resolution) where IntelliJ IDEA is genuinely ahead of VSCode for Java - and for their daily work that's probably worth mentioning. But for the course's AI agent exercises, WezTerm + Codex CLI outside any IDE is the better learning surface, and you can run it in an IntelliJ built-in terminal or WezTerm interchangeably [^6_3].
<span style="display:none">[^6_10][^6_11][^6_12][^6_13][^6_14][^6_15][^6_9]</span>

<div align="center">⁂</div>

[^6_1]: https://www.jetbrains.com/help/ai-assistant/use-custom-models.html

[^6_2]: https://docs.ollama.com/integrations/jetbrains

[^6_3]: https://tessl.io/blog/jetbrains-joins-agent-client-protocol-to-open-ai-coding-agents-to-any-ide/

[^6_4]: https://blog.jetbrains.com/ai/2026/01/acp-agent-registry/

[^6_5]: https://blog.jetbrains.com/ai/2026/01/codex-in-jetbrains-ides/

[^6_6]: https://www.reddit.com/r/Jetbrains/comments/1rg61k9/how_do_i_use_a_local_coding_agent_with_jetbrains/

[^6_7]: https://youtrack.jetbrains.com/projects/LLM/issues/LLM-23964/Unable-to-add-custom-model-from-custom-Open-AI-endpoint-to-Codex-integration-in-JetBrain-AI

[^6_8]: https://www.jetbrains.com/help/air/supported-agents.html

[^6_9]: https://youtrack.jetbrains.com/projects/WRS/articles/SUPPORT-A-1903/How-to-use-JetBrains-AI-Assistant-with-local-models-for-free

[^6_10]: https://appstackbuilder.com/blog/how-to-run-ai-locally-ollama-2026

[^6_11]: https://github.com/Stream29/ProxyAsLocalModel

[^6_12]: https://dev.to/formulahendry/vs-code-acp-client-extension-conect-to-claude-gemini-codex-opencode-qwen-code-and-so-on-3552

[^6_13]: https://www.jetbrains.com/ai-assistant/

[^6_14]: https://zed.dev/blog/jetbrains-on-acp

[^6_15]: https://www.reddit.com/r/Jetbrains/comments/1ri8x18/built_a_free_opensource_jetbrains_plugin_to_use/


---

# I will also show them IntelJ MCP server that provides it's tools to agents, so even the codex or Claude agent can see and understand what they see in IntelliJ.

Additionally I will show them how to configure custom agents and skills for Java specific workflows. and we will create exercises to let the test how they work.

on the last course we created detailed PRD and ADR with all the details and then let the Claude Code just make a plan, create tasks and delegate to specialised sub agents until it finished full app.

but:

1. afaik Claude is better suited for this kind of autonomous workflow, where codex work better with more manual control when we want human in the loop
2. it was strange that for most of the course we were configuring everything, CLAUDE.md files, agents, mcp, skills, adr, prd, wireframes, and full description if system design (done by Claude with Playwright mcp and visiting their website to get exact design tokens). But they did not code and have any effects of work during that time... then we started agents and... they had nothing to do because agents just run autonomously and what even worse ask for permissions for a long time (I did a mistake and didn't show them sandboxing at Claude so they preferred to accept most of the commands instead fo sandbox with autoaccept)

so I'm not sure how to organize this process this time.

maybe small micro side-project after each module to let the test what they build?

And then, when everything is configured, we set auto accept inside a sandbox so they can make full long agent job to build the main app but without stearing on the screen and accepting, so we can make another exercise in this time and maybe even better delegate this long running project/plan to cloud agents if they also can work in the same way with sub-agents and mcp tools and skills to validate they work results same as on my local machine - can they do this? it may be a good case where to delegate to cloud

when agents are working in this bigger app we can discuss the cloud integration, GitHub integration, how they can handle this on premises with CLI tools in CICD workflows, etc. when agents finish or need help we should get notification with codex desktop of WezTerm. So we can switch back and discuss how to give feedback to agents and how to validate they work and how to make their internal validation process better so they will write good tests, avoid flacky tests or false poss, etc. and we should finish the app by improving our agentic system and harness.

what do you think?

how would you organize this?

This is a rich pedagogical problem. The data I just found unlocks some important architectural options for the course - let me go through everything properly.

## What You Learned From the Previous Course

The core problem was a **learning experience shaped like a waterfall**: long setup -> sudden autonomous burst -> nothing to do. The fixes are structural, not cosmetic. The key principle for the redesign: **every module must end with something running that a student built, not something the agent built while they watched.**

Three concrete mistakes to explicitly design against this time:

- Setup cost front-loaded -> split across modules, each piece immediately demonstrated
- No sandbox -> students became "accept monkeys", learned wrong habits, didn't see the tool's actual power
- Big final run = passive audience -> the delegation idea you proposed is exactly the right fix


## IntelliJ MCP Server - Confirmed, Auto-Configure Supported

Since IntelliJ IDEA 2025.2, the IDE ships a **built-in MCP server** with one-click auto-configuration for external clients [^7_1]:

> Settings -> MCP Server -> Enable -> Clients Auto-Configuration -> **Auto-Configure** for Codex / Claude Code / Cursor

This will automatically patch the correct `mcp_config.json` for each CLI tool. No manual JSON editing needed [^7_1]. The MCP server exposes tools for code navigation, refactoring, build execution, run configurations, and symbol search using the IDE's actual index [^7_2]. For a Java Spring AI backend this is genuinely powerful - the agent can do project-wide renames, see compilation errors in real time, and trigger Gradle/Maven builds as proper tool calls.

This is absolutely worth showing - it's one of the strongest demonstrations of why MCP matters, because it takes a closed IDE and makes it transparent to any external agent. A 15-minute demo block showing Codex refactoring a Java class through IntelliJ's own symbol index is more compelling than any slide about MCP.

## Codex Cloud Agents - What They Actually Are

This matters for your delegation idea. The four surfaces share the same model brain but work differently [^7_3]:


| Surface | Where it runs | MCP support | Sub-agents | Result delivery |
| :-- | :-- | :-- | :-- | :-- |
| CLI (local) | Their machine | ✅ Full (any local/network MCP) | ✅ Full | Live in terminal |
| Desktop App | Their machine | ✅ Full | ✅ Built-in parallel worktrees | Visual diff review |
| Cloud Tasks | OpenAI infra | ⚠️ External MCPs only (no localhost) | ✅ | PR on GitHub + `codex apply <ID>` |
| IDE Extension | Their machine | ✅ Shared with CLI | ✅ Delegates to CLI | Inline in editor |

Cloud tasks run on OpenAI's managed environment [^7_3]. This has a critical implication for your use case: **internal bank MCPs (like their IntelliJ MCP server) are not reachable from cloud tasks**. But for the course specifically - where participants have public internet access, ChatGPT Plus subscriptions, and the demo app repo is on GitHub - cloud tasks work perfectly. The agent creates a PR with the completed work, and they `codex apply <TASK_ID>` to pull it in locally [^7_3].

The other important piece: Codex itself can be **exposed as an MCP server** that an Agents SDK orchestrator calls [^7_4]. The pattern looks like this:

```python
# Designer agent (e.g. GPT-5.5) -> spawns -> Developer agent (Codex as MCP)
async with MCPServerStdio("codex", {"command": "npx", "args": ["-y", "codex", "mcp-server"]}) as codex_mcp:
    developer = Agent("Developer", mcp_servers=[codex_mcp], ...)
    designer = Agent("Designer", model="gpt-5.5", handoffs=[developer])
    await Runner.run(designer, "Build the Spring API for user management")
```

This is the most advanced pattern worth showing - not just "Codex runs sub-agents" but "Codex is a tool that a meta-orchestrator calls, with sandbox and approval policy set per-call" [^7_4].

## Course Structure - Redesigned

Based on everything discussed in this whole conversation, here's how I'd organize it:

### Day 1 - Ground Floor, Running Immediately

**Module 1: Environment + First Run (2h)**

- WezTerm setup, `sandbox = "elevated"` (Windows) or Landlock (WSL2) configured **before the first prompt**
- First exercise: `codex "explain this Java file"` with `--approval-mode suggest` - they see the tool work, understand the approval loop, and the sandbox is already on
- End result: working Codex with sandbox, they've seen one complete interaction

**Module 2: AGENTS.md + Skills (2h)**

- Write an `AGENTS.md` together for the demo project skeleton (just a Spring Boot hello-world stub you pre-scaffold)
- Create one custom skill (e.g., `java-test-writer`) and immediately run it on one class
- End result: a skill that generates a JUnit test. They wrote the skill, they ran it, they see a test file appear

**Module 3: MCP - IntelliJ Server (1.5h)**

- Auto-configure IntelliJ MCP for Codex live in the room
- Exercise: `codex "rename the UserService class to CustomerService project-wide"` - runs through IntelliJ's symbol index, not grep
- Brief contrast: what the same task looks like without MCP (dumber, slower, misses some references)
- End result: they've seen the difference MCP makes on a real Java project task


### Day 2 - Agent Orchestration + The Delegation Model

**Module 4: Sub-agents + Multi-agent patterns (2h)**

- Show `spawn_agents` with a CSV batch job on a small multi-file task
- Exercise: split a task (e.g., "add validation to 5 endpoints") into 5 parallel sub-agents, let it run, review the merge
- Important: configure `--approval-mode never` inside sandbox **right now** so they experience what autonomous actually feels like without the accept-spam you had last time
- End result: they've orchestrated a parallel agent job and reviewed results

**Module 5: Planning Phase - PRD + ADR + System Design (2h, but different from last time)** The key insight from last time: **don't do all planning first then code**. Instead:

- Write PRD together (~30 min) - but write it as AGENTS.md instructions, not a separate document
- Create the agent harness (specialized agents: `architect`, `spring-coder`, `react-coder`, `test-writer`, `reviewer`) - (~45 min)
- **Immediately test each agent on a micro-task** so they see each one work before wiring them together
- End result: a configured, tested harness they understand because they've seen each piece individually

**Module 6: Launch the Big Job -> Switch Context (the clever part)**

This is your best pedagogical move. Structure it like this:

1. **Launch the full app build** as a Codex Cloud Task (or local with `--detach` + Codex Desktop notification) - sandbox on, `approval-mode never`, agents fully delegated
2. **The moment it starts running**, switch the room's attention entirely: "The agents are working. We don't watch them. Let's talk about what happens in a real bank environment"
3. **During the run** cover: cloud vs on-premises CLI agents, GitHub Actions integration with `codex exec`, CICD patterns, how to structure agent feedback channels, how to prevent prompt injection in AGENTS.md

When Codex Desktop or WezTerm notifies that an agent needs input or has finished [^7_3]:

4. **Return to the running job together**: review the PR/diff, discuss what went well, identify what failed or was wrong
5. **Module 7 becomes live debugging**: how to improve the harness, write better AGENTS.md constraints, fix flaky tests, add validation assertions that sub-agents must run before reporting done

This mirrors real professional use - the skill being taught is **not watching the agent, it's designing the system so you don't have to**.

### Day 3 - Alternatives, Real Work, Hardening

**Module 8: Claude Code as contrast (1.5h, OpenRouter)**

- Quick setup with OpenRouter, show bash-first philosophy vs Codex RPC tools
- Same task from Module 4 run with Claude Code - discuss the token burn difference, why bash-first can be more flexible but less controlled
- Show Claude Code's VM sandbox as conceptual contrast to Codex Landlock
- No full project, just the contrast exercise

**Module 9: Self-hosted model path (1h)**

- Configure Codex CLI profile pointing at Ollama (or OpenRouter GLM 5)
- Run the Module 2 exercise again with GLM 5 - let them feel the quality gap vs the current Codex/Claude Code baseline.
- Frame it as: "this is what your actual work setup will look like, and this is the quality you're working with - here's how to compensate with better AGENTS.md"

**Module 10: Validation, Testing, Anti-patterns (1.5h)**

- How to write AGENTS.md rules that force test-before-commit
- Anti-flaky-test patterns (explicit assertions, no `time.sleep`, test isolation requirements)
- Prompt injection defense in AGENTS.md: explicit scope restrictions, `disallowedCommands`, file path whitelists
- Live exercise: deliberately break an agent with a malicious AGENTS.md instruction, then fix it


## On the "Human in the Loop" Philosophy

Your intuition that **Claude Code suits full autonomy better while Codex suits human-in-the-loop better** is well-supported [^7_5][^7_6]. Claude burns 4× more tokens than Codex on identical tasks [^7_5] - which for a professional autonomous run is acceptable, but for a course where students are learning to steer, it's expensive and creates passivity. Codex's tighter approval model and explicit sub-agent orchestration makes it **better for teaching**, even if Claude's unconstrained autonomy sometimes produces a better single-shot result [^7_6].

The concrete rule worth teaching: **for learning, more human checkpoints = more learning. For production runs, fewer checkpoints = more throughput. Design your harness for production, but run it in supervised mode during development.** The sandbox plus `approval-mode` spectrum gives them the knob to tune this, which is itself the most important thing they can leave the course understanding.
<span style="display:none">[^7_10][^7_11][^7_12][^7_13][^7_14][^7_15][^7_7][^7_8][^7_9]</span>

<div align="center">⁂</div>

[^7_1]: https://www.jetbrains.com/help/idea/mcp-server.html

[^7_2]: https://mcpmarket.com/tools/skills/jetbrains-ide-integration

[^7_3]: https://blakecrosley.com/guides/codex

[^7_4]: https://developers.openai.com/codex/guides/agents-sdk/

[^7_5]: https://morphllm.com/comparisons/codex-vs-claude-code

[^7_6]: https://safeclaw.io/blog/ai-coding-agents-2026

[^7_7]: https://www.reddit.com/r/codex/comments/1ri5m0f/cli_is_all_you_need_do_we_really_need_mcps/

[^7_8]: https://serenitiesai.com/articles/claude-code-vs-codex-cli-2026

[^7_9]: https://manveerc.substack.com/p/mcp-vs-cli-ai-agents

[^7_10]: https://developers.openai.com/codex/changelog?type=codex-cli

[^7_11]: https://tembo.io/blog/coding-cli-tools-comparison

[^7_12]: https://github.com/openai/codex/issues/11701

[^7_13]: https://blog.jetbrains.com/ai/2025/09/introducing-claude-agent-in-jetbrains-ides/

[^7_14]: https://itecsonline.com/post/claude-code-codex-cli-ai-agents-beyond-coding-2026

[^7_15]: https://github.com/howardpen9/coding-cli-tracker/issues/9
