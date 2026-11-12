# Codex voice, `codex queue` and ChatGPT Enterprise chat credits

*Research date: 30 October 2026. Questions raised by participants during the course. Web research by an agent (Gemini via Antigravity), checked by the trainer against the official pages cited below and against Codex CLI 0.165-0.166 on Linux. Pricing and limits change often; check the linked Help Center pages before relying on a number.*

## Summary

- **Enterprise chat and credits:** on credit-based ChatGPT Enterprise, **Instant** chat costs 0 credits. **Thinking** costs **10 credits per message** whatever the reasoning effort (Medium, High and Extra High cost the same), **Pro** 50, image generation 5 and deep research 50, and they are taken from the shared workspace pool from the first message. On token-based Enterprise every request is billed in USD per token. Business, Plus and Pro use included per-seat allowances first.
- **What participants heard was almost right:** "simple chat is free, reasoning costs credits even in chat" matches the rate card. The free tier is Instant, not a "low" reasoning level, and a higher effort does not raise the per-message price on credit-based plans.
- **Chat and Work:** the new ChatGPT desktop app (28.10.2026) puts Chat, Work and Codex in one app, but billing stays separate: Work is metered like Codex, Chat keeps chat rates. A merge of Chat and Work limits is not rolling out; a notice suggesting it was published by mistake.
- **Voice update, 4 November:** Codex CLI `/voice` and desktop Voice use hosted speech services; they are different from editable composer dictation and Handy's local ASR. For checked Polish prompts across apps when local audio processing and control matter, start with Handy; use native Voice for a live conversation and task steering. See section 3 for data flow, availability and the limits of the comparison.
- **`codex queue`:** works in 0.165-0.166. A message queued with `Tab` in the TUI is lost when you quit Codex; it is not saved with the session. It adds a message to an existing session from another terminal or script; `--resume` (0.166) also wakes a session that is not loaded. In the TUI, `Tab` queues a follow-up for the next turn and `Enter` steers the running turn.

## 1. Does ordinary chat use credits on ChatGPT Enterprise?

It depends on the contract and the model, not on the Chat/Work tab alone.

| Chat mode | Credit-based Enterprise (per message) |
|---|---|
| Instant | 0 credits (unlimited, abuse guardrails) |
| Thinking, GPT-6 (Medium, High, Extra High) | 10 credits |
| Pro (GPT-6 Pro) | 50 credits |
| Image generation | 5 credits |
| Agent mode in chat | 30 credits |
| Deep research | 50 credits per task |

- The rate card FAQ states that a higher reasoning effort does not change the per-message rate: the model sets the price.
- **Credit-based Enterprise** has no per-seat allowance in front of the pool, so every Thinking, Pro, image or deep research message is paid from the workspace credits. Admins limit this with model/tool access and group spend controls.
- **Token-based Enterprise** (USD pricing) has no credit pool. Chat, Work and Codex are billed per million tokens; a higher effort produces more tokens and so costs more.
- **Business, Plus and Pro:** Instant is effectively unlimited, and Thinking/Pro/deep research first use the seat's included allowance. Business credits are optional overflow after a seat runs out.
- ChatGPT Work and Codex are not billed per message: on credit-based plans they use credits per token.

Sources: [Flexible pricing for Enterprise, Edu and Business](https://help.openai.com/en/articles/10427845-flexible-pricing-for-the-enterprise-edu-and-business-plans), [ChatGPT rate card (Business, Enterprise/Edu)](https://help.openai.com/en/articles/11481834-chatgpt-rate-card-business-enterpriseedu), earlier course research [ChatGPT subscriptions vs Enterprise credits](chatgpt-subscription-vs-enterprise-credits-2026-10-12.md).

## 2. Are Chat and Work being merged?

- **Done:** on 28.10.2026 the Codex desktop app became the new ChatGPT desktop app with Chat, Work and Codex. Chat and Work share Recents and Projects and are switched with a toggle; Codex keeps its own view. Source: [Moving to the new ChatGPT desktop app](https://help.openai.com/en/articles/20001276-moving-to-the-new-chatgpt-desktop-app).
- **Not happening yet:** a shared limit for Chat and Work. A checkout notice suggesting it appeared by mistake; the head of ChatGPT and Codex said the merge is not rolling out (tech press reports, no official Help Center page).
- **Billing today:** Work uses the same usage and billing structure as Codex; Chat keeps chat rates (section 1). On 29.10.2026 Work/Codex allowances were doubled for Pro and Business Premium.

## 3. Voice, dictation and local transcription

*Updated: 4 November 2026. Public documentation and Codex CLI 0.166.0 source were checked; no microphone recording or controlled Polish accuracy benchmark was run for this update.*

### Which product and which action?

The terminal tool is **Codex CLI**. ChatGPT's desktop app exposes Chat, Work and Codex; "ChatGPT CLI" is not the name of the terminal product in this comparison. In the desktop app, **Start voice chat** starts an ongoing spoken conversation. **Dictate** turns speech into editable prompt text before sending. Voice can interrupt, steer and coordinate tasks; dictation alone does not start those tasks. [Voice](https://learn.chatgpt.com/docs/features/voice), [Dictation](https://learn.chatgpt.com/docs/prompting#use-voice-dictation).

| Path | Speech processing and output | Best use | Trade-off |
|---|---|---|---|
| Codex CLI `/voice` where available | Microphone audio goes to a hosted realtime service; spoken interaction can hand work to the coding agent | Hands-free discussion, short follow-ups and steering while work continues | Needs a working network/audio setup and account entitlement; audio leaves the computer |
| Desktop **Start voice chat**, in Chat/Work/Codex | Hosted conversational voice; OpenAI identifies the voice layer as GPT-Live | Discuss a problem, ask for progress, redirect tasks | Plan, rollout, workspace controls and a separate active voice session affect availability |
| Desktop composer **Dictate** | Recorded audio is sent to OpenAI for transcription, then returned as editable prompt text | Compose a longer prompt without immediately acting on it | Review the recognized words before sending; exact transcription backend is not identified by the checked product page |
| Handy with local ASR and cloud cleanup disabled | A downloaded recognition model runs on the device and pastes text into the focused field | Dictate into Codex CLI, desktop, editor or another app with the same shortcut | Uses local RAM/CPU/GPU; requires installation/model download; does not itself converse or coordinate an agent |
| OS or IDE dictation | Depends on the selected OS, extension and language pack | An existing accessible input method | Check that provider's data flow; an OS microphone icon does not establish offline inference |

Sources for the table: [desktop voice](https://learn.chatgpt.com/docs/features/voice), [desktop dictation](https://learn.chatgpt.com/docs/prompting#use-voice-dictation), [dictation data flow](https://help.openai.com/en/articles/12168547-voice-dictation-faq), [pinned CLI realtime transport](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/core/src/realtime_conversation.rs), [Handy workflow](https://github.com/cjpais/Handy#how-it-works). The final OS/IDE row is a configuration check, not a claim that every OS uses the same backend.

### Why `/voice` is not local ASR

Codex 0.166.0's public implementation routes captured audio through Realtime WebSocket/WebRTC calls and receives remote audio/events. Microphone capture and audio playback happen locally; recognition/conversation is not thereby local model inference. Its source has separate realtime model selection and configurable defaults, so the coding model shown for a task does not establish which exact speech deployment processed that recording. Do not label every CLI or desktop voice session "Whisper", or assume an installed local LLM receives microphone input. No actual session routing/model telemetry was measured here. [CLI source](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/core/src/realtime_conversation.rs), [CLI microphone controls](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/chatwidget/realtime.rs).

Desktop Voice is documented as powered by GPT-Live; the task's selected model handles the work it directs. That is a voice layer plus an agent workflow, rather than evidence that the selected text model is itself an audio model. [Desktop Voice](https://learn.chatgpt.com/docs/features/voice).

ChatGPT also distinguishes **Live**, **Advanced** and **Standard** voice options, depending on the surface and account. Standard transcribes before generating a reply; Live supports simultaneous listening/speaking. These options are not interchangeable names for Codex CLI or Handy, and a Voice transcript need not be verbatim. [ChatGPT Voice FAQ](https://help.openai.com/en/articles/20001274-chatgpt-voice).

**Version check:** this machine's `codex --version` returned `0.166.0`; `codex features list` reported `in_app_voice` and `in_app_dictation` as stable/enabled and `realtime_conversation` as removed. `in_app_dictation` is a desktop-app control: its presence in the CLI's shared feature list does **not** prove that the TUI has composer dictation or restore the old hold-Space workflow. The configuration reference still describes `features.realtime_conversation` for an experimental CLI `/voice` command. Do not use a flag alone as proof of runtime availability. [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

Pinned 0.166.0 source independently registers `/voice` with a start/stop action and `/voice settings`; the command list can hide it behind `voice_command_enabled`. This establishes that the command is implemented in that release, while a successful session still depends on the running client's availability checks, account and audio/network setup. No actual voice session was started here. [Slash-command registration](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/slash_command.rs), [visibility filter](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/bottom_pane/slash_commands.rs).

### Practical controls and alternative input methods

- **Codex CLI 0.166:** `tui.keymap.chat.toggle_voice` starts/stops the conversation; `tui.keymap.chat.toggle_voice_mute` toggles its microphone. The pinned tests verify configurable bindings and unbinding; defaults can yield to conflicting shortcuts. Check the visible hint or configure these actions rather than assuming a universal key. [Keymap fields](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/config/src/tui_keymap.rs), [binding tests](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/tui/src/keymap/voice_tests.rs).
- **Windows voice typing:** focus a text field and press `Win+H`. Microsoft documents online Azure Speech recognition and Polish support; this is a separate service from Codex and from local Handy ASR. [Microsoft voice typing](https://support.microsoft.com/en-us/accessibility/windows/use-voice-typing-to-talk-instead-of-type-on-your-pc).
- **VS Code:** current built-in dictation uses `Ctrl+Alt+V` for a writable editor and `Ctrl+I` for chat on Windows/Linux. Supported desktop platforms use local ASR by default after the model download; web dictation streams audio to Microsoft. Optional LLM cleanup sends the transcript separately. The **VS Code Speech extension** remains a documented alternative for unsupported desktop platforms; its Marketplace page also documents `Ctrl+Alt+V` for editor dictation and local audio processing. These are VS Code input methods, not a Codex extension voice button or CLI feature. [Current VS Code guide](https://code.visualstudio.com/docs/configure/accessibility/voice), [Speech extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode.vscode-speech).

### Polish and mixed Polish/English

There is no controlled result in these sources showing that ChatGPT/Codex Voice or dictation is more accurate than Handy for this group's Polish, accents or developer vocabulary. A conversational response that sounds fluent is not a scored transcription benchmark. The [Polish Handy research](speech-to-text-models-polish-handy.md) distinguishes model-card coverage, public benchmark scores and the trainer's dated observations.

Practical course procedure:

1. Start a voice discussion with: "Mów po polsku. Nazwy narzędzi, polecenia i identyfikatory zachowuj w oryginale. Gdy czegoś nie rozumiesz, dopytaj". This is a proposed instruction, not a guarantee of recognition quality.
2. For a prompt or command that must be exact, prefer **Dictate** or Handy, inspect the resulting text, then submit it. Check negation, numbers, paths, `Context7`, `OpenRouter`, `Jev`, `PRD` and `ADR`.
3. In Handy, use a model whose catalog declares Polish support; language/translation controls depend on the selected model. Keep Polish transcription and translation to English as separate tests. ChatGPT documents **Settings > Voice > Language** for a preferred spoken language and accepts a spoken request to switch languages. Do not assume that setting is also a Codex CLI control or a custom dictionary shared with Handy. [Language guidance](https://help.openai.com/en/articles/20001274-chatgpt-voice#change-your-preferred-language).
4. Compare a short synthetic Polish prompt, a technical PL/EN prompt and a correction containing "nie usuwaj". Record recognition errors and time to a checked prompt separately from the usefulness of the agent's response. Do not promise a winner without that test.

### Privacy and practical choice

**Handy is the starting recommendation for checked Polish dictation across apps when local audio processing matters.** Native Voice is the better fit for a live discussion and steering an active agent. This recommendation compares interaction and data flow; it is not a measured accuracy or speed ranking.

Handy can work offline after the model is downloaded. Its optional cloud post-processing sends the transcript and selected prompt directly to the chosen provider; local ASR plus remote cleanup is therefore a mixed pipeline. Local history may retain recordings and transcripts, so review retention as well as network use. Pasting the result into a hosted agent and submitting it sends the text to that agent even when the original audio stayed local. [Handy privacy policy](https://handy.computer/privacy).

ChatGPT dictation sends the recording before you press Send on the resulting text. Its FAQ says audio is retained with chat history, subject to deletion exceptions; review the current policy and account data controls rather than assuming Dictate is transient local recording. [Dictation privacy](https://help.openai.com/en/articles/12168547-voice-dictation-faq).

OpenAI's local-execution guidance explicitly distinguishes device-side tool execution from hosted inference. Audio, task context and optional screen/app context need their own review; a Business workspace's default non-training commitment does not mean the audio never leaves the device. Voice obeys the directed task's permissions. For a classroom demonstration, use a synthetic prompt, keep sensitive windows closed, and stop/mute the microphone before switching to unrelated work. [Local security and data handling](https://learn.chatgpt.com/docs/enterprise/chatgpt-work-local-security), [Voice permissions and screen context](https://learn.chatgpt.com/docs/features/voice).


## 4. `codex queue` and follow-up messages

- **From another terminal or a script:**

  ```bash
codex queue --thread "<session-id-or-name>" --message "Run the integration tests next"
```

  With `--resume` (added in 0.166.0) Codex also tries to resume a session that is not loaded. If the session was interrupted mid-turn, the message is stored but not sent until you resume the session yourself.
- **In the TUI while a turn is running:** `Tab` queues the text as the next turn, `Enter` steers the current turn at the next safe point, `Shift+Left` edits the last queued message.
- **Continue an earlier session:** `codex resume` (picker), `codex resume --last "next prompt"`, or non-interactively `codex exec resume --last "next prompt"`.

Checked locally with `codex queue --help` on 0.165.0 (`--thread`, `--message`, `--resume`, `--remote`). Source: [openai/codex releases, rust-v0.166.0](https://github.com/openai/codex/releases).

### Does a message queued with Tab survive leaving the session?

**No.** Scenario from the course: during a running turn you type a message and press `Tab`, so it is queued instead of steering; you switch to another agent view and back, then quit Codex and later `codex resume` the session. The queued message is gone.

- In the TUI source (`codex-rs/tui/src/chatwidget/user_messages.rs`, `ThreadInputState.queued_user_messages`, commit `2546265` of 30.10.2026) the queue is kept **only in the memory of the running TUI**. When you switch between agent views, the TUI saves it per thread in memory and restores it, so navigation alone does not drop it. Nothing writes it to the session file, so quitting Codex loses it and `codex resume` cannot bring it back.
- The desktop app has the same reported problem: [openai/codex#32715](https://github.com/openai/codex/issues/32715) "Codex Desktop silently loses queued follow-up messages after restart" (open).
- `codex queue --thread ... --message ...` is different: it adds the message through the app server, so it is stored with the thread and survives the TUI closing; `--resume` then wakes the thread.

How not to lose a follow-up: wait until the turn finishes before quitting, use `Enter` to steer the running turn instead of queueing, or copy the queued text before you quit. For work you hand over to a later session, use `codex queue`.
