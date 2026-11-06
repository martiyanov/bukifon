# Bukifon — English documentation index

Open-source desktop synth / sampler / sequencer for 3D printing. 42 keys, 16 encoders,
5″ 800×480, 10 jacks, 2 faders, microphone; open KiCad hardware, C++ firmware, module SDK.

## Start here

| Doc | What |
|---|---|
| [quick-start.md](quick-start.md) | Idea in 10 minutes (EN) |
| [docs/75](../75-release-readiness.md) | v1.0-rc gates and status |
| [docs/76](../76-known-limitations.md) | Honest limitations (before buying) |
| [docs/81](../81-faq.md) | FAQ (RU, key points below) |
| [docs/79](../79-competitors-2026.md) | Competitors 2025–2026 and positioning |
| [docs/press/](../press/) | Press kit (boilerplate RU/EN, images) |
| [docs/77](../77-quick-start.md) | Quick start (RU, full) |

## Key facts

- **Price target:** P4 Standard **$299**, Full Bundle $399; S3-lite $199. Not on sale yet.
- **Hardware:** CORE-2 rev.3 (ESP32-P4 + C6, USB HS UAC2 8×8, 6-layer), PANEL-2 rev.3
  (42 Choc, 16 EC11, I2S MEMS mic, 4-layer), PWR-2 rev.1 (2-oz, BMS); PRE-FREEZE.
- **Firmware:** 365 host tests, UI 7 tabs, 12 tracks (4 internal + 8 external MIDI),
  GEN engine, project v2 `.bkfp`, factory self-test 21, Module SDK v0.2.
- **Cases:** A 302 g, B 277 g, **B-light 231.4 g / 11.2 h**, C 314 g; B_mic/C_mic options.
- **Openness:** KiCad (CERN-OHL-S-2.0), C++ (GPL-3.0-or-later), docs (CC-BY-SA-4.0).

## Limits (short)

S3-lite uses an SPI display and stereo USB; looper/vocoder are v1.1; microphone is for
ideas/beatbox, not studio vocals; battery is an option, not in the first batch; CC p-lock only
on external tracks (1 CC per step); Module API v0 is experimental.

## Build / buy

- Assembly in Russia (Moscow/SPb/Nizhny Novgorod): [docs/72](../72-assembly-workshops.md).
- Day 1 with hardware: [docs/80](../80-day1-bringup.md).
- FAQ (RU): [docs/81](../81-faq.md). Contact: GitHub Issues.
