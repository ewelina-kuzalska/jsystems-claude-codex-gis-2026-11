---
title: Polish and Polish-accented English dictation in Handy
date: 2026-10-20
reviewed: 2026-11-04
tags:
  - ai/speech-to-text
  - polish-nlp
  - handy-computer
  - canary
---

# Polish and Polish-accented English dictation in Handy

## Practical recommendation

Start with **NVIDIA Canary 1B v2** for Polish dictation and bilingual Polish/English work in [Handy](https://handy.computer/), if it is available in your installed model catalog. Local trials recorded on 20 October 2026 support this starting choice. It is a useful starting point, not a demonstrated universal winner for Polish accents.

Compare it with **Parakeet TDT 0.6B v3** and a multilingual **Whisper** model on the same recordings before choosing your daily model. Distinguish English spoken with a Polish accent from Polish speech translated into English: these are different tasks.

## What the sources establish

- [NVIDIA's Canary 1B v2 model card](https://huggingface.co/nvidia/canary-1b-v2) confirms Polish and English transcription, plus translation between English and the other supported languages. The original Canary 1B and Canary 1B v2 have different language coverage; select **v2**.
- [NVIDIA's Parakeet TDT 0.6B v3 model card](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3#performance) reports Polish WER of **7.31% on FLEURS** and **7.28% on MLS**. Lower WER means fewer word errors. Those scores do not measure Polish-accented English or punctuation quality.
- The checked Canary card reports **8.40% WER averaged across 25 FLEURS languages**, not a Polish-only score. Do not interpret that multilingual average as a Polish-only score or a benchmark win for Polish.
- [Handy's model manager](https://github.com/cjpais/Handy/blob/main/src-tauri/src/managers/model.rs) contains a migration reference for Canary 1B v2 to `handy-computer/canary-1b-v2-gguf`. Catalog contents, quantizations and accelerators depend on the app version; this source is not proof that every released build offers the same choices.

Multilingual training makes accent robustness a reasonable hypothesis, but the checked sources do not provide a controlled Polish-accented English comparison. English-only models are not automatically unsuitable for accented English.

## Local observations from 20 October

Local trials used Handy 0.9.8 on Ubuntu with a GTX 1650 (4 GB), using Canary 1B v2 Q5_K_M. The trials were not independently repeated:

- The trainer reported no noticed errors in one natural Polish passage, including diacritics and the model name. There is no retained reference audio or scored comparison in this repository, so this is not a measured 0% WER result.
- Polish speech produced English output when English was selected, even with translation shown as disabled. A model-name substitution occurred. Treat this as observed behavior of that setup, not a supported configuration recipe for other versions.
- Switching languages within one recording reportedly truncated output. Starting a fresh recording after switching languages was a practical workaround; the proposed attention/decoder explanation was not established.
- The notes reported transcription in under a second and approximately 1.24 GB total GPU memory. Audio duration, repeated timings and isolated process measurements were not retained. These observations establish neither zero CPU use nor thermal efficiency; 1.24 GB is about 31% of 4 GB.

## Participant workflow

1. For Polish text, choose Polish transcription and check that translation is disabled. Record a short sample before dictating a long prompt.
2. For English output, test English transcription and Polish-to-English translation separately using the controls supported by your installed version. Selecting English alone is not a portable translation instruction.
3. Use a fresh recording when switching spoken languages if mixed speech gets truncated.
4. Check names, numbers, code identifiers and negations before pasting the result into an agent. Optional LLM cleanup can improve formatting but can also change meaning; compare it with the raw transcript.

Copyable [transcription and cleanup prompts](../Prompt%20examples/Handy.computer%20-%20transcription%20prompts.md) are provided separately. Local ASR and cloud LLM cleanup have different data boundaries: enabling remote cleanup sends transcript text to that provider.

## How to compare models on your own voice

Use the same microphone and saved synthetic recordings for each model: natural Polish with diacritics, English spoken in your own accent, developer names and numbers, and a separate translation sample. Include negations and one mixed-language sample. Write a reference transcript first; score word errors separately from punctuation and translation fidelity. Record the app version, model, quantization, accelerator, audio duration and processing time. Repeat several samples before choosing a model.

Catalog rankings and a successful sample do not establish zero hallucination risk or a universal winner for a particular speaker.

## Handy versus ChatGPT/Codex voice (4 November 2026)

Use Handy to prepare text in any application; use native Voice to converse with an agent. The detailed [Codex and desktop comparison](codex-voice-queue-enterprise-chat-credits-2026-10-30.md#3-voice-dictation-and-local-transcription) separates `/voice`, desktop **Start voice chat**, composer **Dictate** and OS/IDE dictation. None of the local observations above is a head-to-head benchmark against native Voice.

### Local does not mean nothing is retained

Ordinary Handy recognition runs on the device. The official privacy policy says audio/transcripts can remain in local history, and saved entries can remain until deleted. Review history limits and recording retention on shared machines; uninstalling the application may leave its data directory. Updates and model downloads make network requests without sending ordinary transcription content. [Handy privacy policy](https://handy.computer/privacy).

Optional cloud cleanup sends the transcript and chosen prompt to the configured provider. Keep it disabled for an entirely on-device speech-to-text step, or deliberately use an approved local endpoint. After pasting, review and submit the prompt yourself: the destination agent's own data handling then applies. [Handy privacy policy](https://handy.computer/privacy).

### Choose the installed model, not just a brand

The current README lists multilingual Whisper choices and Parakeet V3, while the model manager retains Canary v2 migration/discovery support. The downloadable catalog and local model metadata decide which language and translation controls are available in a particular installation. The existing Canary recommendation is based on the dated local trial, not a promise that every new install has the same model or hardware path. [Handy README](https://github.com/cjpais/Handy#how-it-works), [model catalog and discovery](https://github.com/cjpais/Handy/blob/main/src-tauri/src/managers/model.rs), [model capability handling](https://github.com/cjpais/Handy/blob/main/src-tauri/src/managers/model_capabilities.rs).

For a short comparison, use the same synthetic Polish text, then a second prompt containing English identifiers and a negation. Compare raw transcription, cleanup changes, recognition/processing delay and time spent correcting. Check that Polish stays Polish, English identifiers stay exact, and a phrase such as "nie usuwaj plików" keeps its negation. Language support and catalog ratings do not guarantee perfect mixed-language recognition.
