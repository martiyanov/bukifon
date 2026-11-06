// SPDX-License-Identifier: GPL-3.0-or-later
// UI localisation RU/EN (docs/61, docs/66).  Every screen string is looked up
// through tr(UiKey); the language is a global setting persisted in project v2.
#pragma once

#include <cstddef>
#include <cstdint>

namespace bukifon {

enum class Lang : uint8_t { Ru = 0, En = 1, Count = 2 };

enum class UiKey : uint16_t {
  // Navigation / pages.
  Main, Seq, Mix, Mod, Gen, Ext, Mic,
  PageMain, PageSequencer, PageMixer, PageModules, PageGen, PageExt, PageMic,
  // Transport / status / context.
  Play, Stop, Rec, Ready, On, Off, Saved, Unsaved, Pass, Fail, Skip, Error,
  Part, Selected, Page, Faders, Pat, Bar, Group, Presets, AbCompare,
  EuclidRing, Mute, Take, Privacy, MicOn, MicMuted, Synth, Sampler, Daw, UsbKbd,
  // Main parameter labels + fixed macros.
  Cutoff, Resonance, EnvAmt, Drive, Attack, Decay, Sustain, Release, Level,
  MacroCut, MacroRes, MacroAtk, MacroRel, MacroDly, MacroDrv, MacroCrsh, MacroMst,
  // GEN page.
  Prob, Euclid, Mutate, Scale, ArpRate, ArpMode, Evolve, Seed,
  // EXT page.
  Ch, Prog, Vel, Len, CcHash, CcVal, Swing, Clk,
  // MIC page.
  Source, Gain, Thresh, Monitor, Beatbox, Sens, RecPad, Kick, Snare, Hat,
  // Self-test / generic errors.
  Timeout, HardwareFail, NotFound, Loading,
  kCount
};

const char* tr(UiKey key);
const char* tr(UiKey key, Lang language);
const char* uiKeyName(UiKey key);
const char* languageName(Lang language);
bool languageFromName(const char* name, Lang* out);  // "RU"/"EN", case-insensitive

Lang getLanguage();
void setLanguage(Lang language);

// True when both RU and EN strings are non-empty (used by tests/CI).
bool uiKeyHasTranslations(UiKey key);

// Host settings stub (real NVS/flash persistence is TODO(hw)).
const char* i18nSettingsPath();
int i18nSaveLanguage(const char* path = nullptr);
int i18nLoadLanguage(const char* path = nullptr);

constexpr int kUiKeyCount = static_cast<int>(UiKey::kCount);

}  // namespace bukifon
