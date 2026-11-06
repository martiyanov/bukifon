// SPDX-License-Identifier: GPL-3.0-or-later
#include "bukifon_i18n.h"

#include <cctype>
#include <cstdio>
#include <cstring>
#include <strings.h>

namespace bukifon {
namespace {

struct Entry {
  const char* name;
  const char* ru;
  const char* en;
};

const Entry kEntries[kUiKeyCount] = {
    {"MAIN", "ГЛАВН", "MAIN"},
    {"SEQ", "СЕКВ", "SEQ"},
    {"MIX", "МИКШ", "MIX"},
    {"MOD", "МОД", "MOD"},
    {"GEN", "ГЕН", "GEN"},
    {"EXT", "ВНЕШ", "EXT"},
    {"MIC", "МИК", "MIC"},
    {"PAGE_MAIN", "ГЛАВНАЯ", "MAIN"},
    {"PAGE_SEQUENCER", "СЕКВЕНСОР", "SEQUENCER"},
    {"PAGE_MIXER", "МИКШЕР", "MIXER"},
    {"PAGE_MODULES", "МОДУЛИ", "MODULES"},
    {"PAGE_GEN", "ГЕНЕРАТОР", "GEN"},
    {"PAGE_EXT", "ВНЕШНИЙ MIDI", "EXT MIDI"},
    {"PAGE_MIC", "МИКРОФОН", "MIC"},
    {"PLAY", "ИГРА", "PLAY"},
    {"STOP", "СТОП", "STOP"},
    {"REC", "ЗАП", "REC"},
    {"READY", "ГОТОВ", "READY"},
    {"ON", "ВКЛ", "ON"},
    {"OFF", "ВЫКЛ", "OFF"},
    {"SAVED", "СОХР", "SAVED"},
    {"UNSAVED", "НЕ СОХР", "UNSAVED"},
    {"PASS", "УСПЕХ", "PASS"},
    {"FAIL", "СБОЙ", "FAIL"},
    {"SKIP", "ПРОПУСК", "SKIP"},
    {"ERROR", "ОШИБКА", "ERROR"},
    {"PART", "ПАРТ", "PART"},
    {"SELECTED", "ВЫБРАНО", "SELECTED"},
    {"PAGE", "СТР", "PAGE"},
    {"FADERS", "ФЕЙД", "FADERS"},
    {"PAT", "ПАТ", "PAT"},
    {"BAR", "ТАКТ", "BAR"},
    {"GROUP", "ГРУППА", "GROUP"},
    {"PRESETS", "ПРЕСЕТЫ", "PRESETS"},
    {"A/B", "A/B", "A/B"},
    {"EUCLID_RING", "КОЛЬЦО ЕВКЛИДА", "EUCLID RING"},
    {"MUTE", "МЬЮТ", "MUTE"},
    {"TAKE", "ТЕЙК", "TAKE"},
    {"PRIVACY", "ПРИВАТНОСТЬ", "PRIVACY"},
    {"MIC_ON", "МИК ВКЛ", "MIC ON"},
    {"MIC_MUTED", "МИК ВЫКЛ", "MIC MUTED"},
    {"SYNTH", "СИНТ", "SYNTH"},
    {"SAMPLER", "СЭМПЛЕР", "SAMPLER"},
    {"DAW", "DAW", "DAW"},
    {"USB_KBD", "USB-КЛАВ", "USB-KBD"},
    {"CUTOFF", "СРЕЗ", "CUTOFF"},
    {"RESONANCE", "РЕЗОНАНС", "RESONANCE"},
    {"ENVAMT", "ОГИБ", "ENV AMT"},
    {"DRIVE", "ДРАЙВ", "DRIVE"},
    {"ATTACK", "АТАКА", "ATTACK"},
    {"DECAY", "СПАД", "DECAY"},
    {"SUSTAIN", "СУСТЕЙН", "SUSTAIN"},
    {"RELEASE", "РЕЛИЗ", "RELEASE"},
    {"LEVEL", "УРОВЕНЬ", "LEVEL"},
    {"CUT", "СРЕЗ", "CUT"},
    {"RES", "РЕЗ", "RES"},
    {"ATK", "АТК", "ATK"},
    {"REL", "РЕЛ", "REL"},
    {"DLY", "ЗАД", "DLY"},
    {"DRV", "ДРВ", "DRV"},
    {"CRSH", "КРШ", "CRSH"},
    {"MST", "МАСТ", "MST"},
    {"PROB", "ВЕРОЯТ", "PROB"},
    {"EUCLID", "ЕВКЛИД", "EUCLID"},
    {"MUTATE", "МУТАЦИЯ", "MUTATE"},
    {"SCALE", "ГАММА", "SCALE"},
    {"ARP_RATE", "ТЕМП АРП", "ARP RATE"},
    {"ARP_MODE", "РЕЖИМ АРП", "ARP MODE"},
    {"EVOLVE", "ЭВОЛЮЦИЯ", "EVOLVE"},
    {"SEED", "ЗЕРНО", "SEED"},
    {"CH", "КАН", "CH"},
    {"PROG", "ПРОГ", "PROG"},
    {"VEL", "ВЕЛ", "VEL"},
    {"LEN", "ДЛИН", "LEN"},
    {"CC#", "CC#", "CC#"},
    {"CC_VAL", "CC ЗНАЧ", "CC VAL"},
    {"SWING", "СВИНГ", "SWING"},
    {"CLK", "КЛОК", "CLK"},
    {"SOURCE", "ИСТОЧНИК", "SOURCE"},
    {"GAIN", "УСИЛЕНИЕ", "GAIN"},
    {"THRESH", "ПОРОГ", "THRESH"},
    {"MONITOR", "МОНИТОР", "MONITOR"},
    {"BEATBOX", "БИТБОКС", "BEATBOX"},
    {"SENS", "ЧУВСТВ", "SENS"},
    {"REC_PAD", "ЗАП НА ПЭД", "REC PAD"},
    {"KICK", "БОЧКА", "KICK"},
    {"SNARE", "СНЕЙР", "SNARE"},
    {"HAT", "ХЭТ", "HAT"},
    {"TIMEOUT", "ТАЙМАУТ", "TIMEOUT"},
    {"HARDWARE_FAIL", "СБОЙ ЖЕЛЕЗА", "HARDWARE FAIL"},
    {"NOT_FOUND", "НЕ НАЙДЕНО", "NOT FOUND"},
    {"LOADING", "ЗАГРУЗКА", "LOADING"},
};

Lang gLanguage = Lang::En;

}  // namespace

const char* tr(UiKey key, Lang language) {
  const int index = static_cast<int>(key);
  if (index < 0 || index >= kUiKeyCount) return "?";
  const Entry& entry = kEntries[index];
  return language == Lang::Ru ? entry.ru : entry.en;
}

const char* tr(UiKey key) { return tr(key, gLanguage); }

const char* uiKeyName(UiKey key) {
  const int index = static_cast<int>(key);
  return (index >= 0 && index < kUiKeyCount) ? kEntries[index].name : "?";
}

const char* languageName(Lang language) {
  return language == Lang::Ru ? "RU" : "EN";
}

bool languageFromName(const char* name, Lang* out) {
  if (!name || !out) return false;
  if (strcasecmp(name, "RU") == 0 || strcasecmp(name, "ru") == 0) {
    *out = Lang::Ru;
    return true;
  }
  if (strcasecmp(name, "EN") == 0 || strcasecmp(name, "en") == 0) {
    *out = Lang::En;
    return true;
  }
  return false;
}

Lang getLanguage() { return gLanguage; }
void setLanguage(Lang language) {
  if (language == Lang::Ru || language == Lang::En) gLanguage = language;
}

const char* i18nSettingsPath() { return "firmware_language.cfg"; }

int i18nSaveLanguage(const char* path) {
  std::FILE* file = std::fopen(path && path[0] ? path : i18nSettingsPath(), "wb");
  if (!file) return 0;
  const bool ok = std::fprintf(file, "%s\n", languageName(gLanguage)) > 0;
  std::fclose(file);
  return ok ? 1 : 0;
}

int i18nLoadLanguage(const char* path) {
  std::FILE* file = std::fopen(path && path[0] ? path : i18nSettingsPath(), "rb");
  if (!file) return 0;
  char line[16] = {};
  const bool read = std::fgets(line, sizeof(line), file) != nullptr;
  std::fclose(file);
  if (!read) return 0;
  char* end = line;
  while (*end && *end != '\n' && *end != '\r') ++end;
  *end = '\0';
  Lang parsed = gLanguage;
  if (!languageFromName(line, &parsed)) return 0;
  gLanguage = parsed;
  return 1;
}

bool uiKeyHasTranslations(UiKey key) {
  const int index = static_cast<int>(key);
  if (index < 0 || index >= kUiKeyCount) return false;
  const Entry& entry = kEntries[index];
  return entry.ru && entry.ru[0] != '\0' && entry.en && entry.en[0] != '\0';
}

}  // namespace bukifon
