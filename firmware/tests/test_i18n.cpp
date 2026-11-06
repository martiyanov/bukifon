// SPDX-License-Identifier: GPL-3.0-or-later
// UI localisation RU/EN: complete key table, switching, snapshot/context text,
// project v2 persistence and both-language rendering.
#include <cstdint>
#include <cstring>
#include <set>
#include <string>
#include <vector>

#include "bukifon_i18n.h"
#include "storage/project_v2.hpp"
#include "test_framework.hpp"
#include "ui/ui800.hpp"

using namespace bukifon;

namespace {

uint64_t checksum(const ui::Framebuffer800& fb) {
  uint64_t hash = 1469598103934665603ull;
  for (int y = 0; y < fb.height(); y += 5) {
    for (int x = 0; x < fb.width(); x += 5) {
      hash ^= fb.at(x, y);
      hash *= 1099511628211ull;
    }
  }
  return hash;
}

int nonBlack(const ui::Framebuffer800& fb) {
  int count = 0;
  for (int y = 0; y < fb.height(); y += 3) {
    for (int x = 0; x < fb.width(); x += 3) count += fb.at(x, y) != 0 ? 1 : 0;
  }
  return count;
}

}  // namespace

TEST(I18nAllKeysHaveRuEn) {
  CHECK(kUiKeyCount > 60);
  for (int i = 0; i < kUiKeyCount; ++i) {
    const UiKey key = static_cast<UiKey>(i);
    CHECK(uiKeyHasTranslations(key));
    CHECK(tr(key, Lang::Ru) != nullptr && tr(key, Lang::Ru)[0] != '\0');
    CHECK(tr(key, Lang::En) != nullptr && tr(key, Lang::En)[0] != '\0');
  }
  INFO("i18n: all %d keys have non-empty RU and EN strings", kUiKeyCount);
}

TEST(I18nKeyNamesUnique) {
  std::set<std::string> names;
  for (int i = 0; i < kUiKeyCount; ++i) {
    const char* name = uiKeyName(static_cast<UiKey>(i));
    CHECK(name != nullptr && name[0] != '\0');
    CHECK(names.insert(name).second);
  }
  CHECK(static_cast<int>(names.size()) == kUiKeyCount);
  INFO("i18n: key names unique and non-empty");
}

TEST(I18nLanguageSwitch) {
  setLanguage(Lang::En);
  CHECK(getLanguage() == Lang::En);
  CHECK(std::strcmp(tr(UiKey::Selected), "SELECTED") == 0);
  setLanguage(Lang::Ru);
  CHECK(getLanguage() == Lang::Ru);
  CHECK(std::strcmp(tr(UiKey::Selected), "ВЫБРАНО") == 0);
  CHECK(std::strcmp(tr(UiKey::Selected, Lang::En), "SELECTED") == 0);
  CHECK(std::strcmp(languageName(Lang::Ru), "RU") == 0);
  CHECK(std::strcmp(languageName(Lang::En), "EN") == 0);
  Lang parsed = Lang::En;
  CHECK(languageFromName("ru", &parsed) && parsed == Lang::Ru);
  CHECK(languageFromName("EN", &parsed) && parsed == Lang::En);
  CHECK(!languageFromName("DE", &parsed));
  setLanguage(Lang::En);
  INFO("i18n: setLanguage/getLanguage RU/EN and name parsing");
}

TEST(I18nAllKeysNoMissing) {
  for (Lang language : {Lang::Ru, Lang::En}) {
    setLanguage(language);
    for (int i = 0; i < kUiKeyCount; ++i) {
      const char* text = tr(static_cast<UiKey>(i));
      CHECK(text != nullptr);
      CHECK(text[0] != '\0');
      CHECK(std::strcmp(text, "?") != 0);
      CHECK(std::strcmp(text, "<missing>") != 0);
    }
  }
  setLanguage(Lang::En);
  INFO("i18n: every key resolves (no '?' / <missing>) in both languages");
}

TEST(I18nEnglishLengthLimit) {
  for (int i = 0; i < kUiKeyCount; ++i) {
    const char* en = tr(static_cast<UiKey>(i), Lang::En);
    CHECK(std::strlen(en) <= 28);  // cells are 12/18 px, 28 chars max
  }
  INFO("i18n: EN strings fit UI cells (<=28 chars; descriptions excluded by table)");
}

TEST(I18nSnapshotTextSwitches) {
  setLanguage(Lang::En);
  ui::UiSnapshot en;
  ui::uiSnapshotDemo(&en, ui::Screen::Main);
  setLanguage(Lang::Ru);
  ui::UiSnapshot ru;
  ui::uiSnapshotDemo(&ru, ui::Screen::Main);
  int changed = 0;
  for (int i = 0; i < ui::kNumParams; ++i) {
    if (std::strcmp(en.params[i].label, ru.params[i].label) != 0) ++changed;
  }
  CHECK(changed >= 2);
  CHECK(std::strcmp(en.params[0].label, "CUTOFF") == 0);
  CHECK(std::strcmp(ru.params[0].label, "СРЕЗ") == 0);
  CHECK(std::strcmp(en.macros[0].label, "CUT") == 0);
  CHECK(std::strcmp(ru.macros[0].label, "СРЕЗ") == 0);
  setLanguage(Lang::En);
  INFO("i18n: switching language changes snapshot params/macros (>=2 strings)");
}

TEST(I18nContextLineEnglish) {
  setLanguage(Lang::En);
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  snapshot.selectedLabel[0] = '2';
  snapshot.micMuted = false;
  char line[192];
  ui::uiBuildContextLine(&snapshot, line, sizeof(line));
  CHECK(std::strstr(line, "PART") != nullptr);
  CHECK(std::strstr(line, "SELECTED") != nullptr);
  CHECK(std::strstr(line, "FADERS") != nullptr);
  CHECK(std::strstr(line, "REC") != nullptr);
  CHECK(std::strstr(line, "UNSAVED") != nullptr);
  CHECK(std::strstr(line, "MIC ON") != nullptr);
  INFO("i18n: EN context line contains PART/SELECTED/FADERS/REC/MIC/UNSAVED");
}

TEST(I18nContextLineRussian) {
  setLanguage(Lang::Ru);
  ui::UiSnapshot snapshot;
  ui::uiSnapshotDemo(&snapshot, ui::Screen::Main);
  char line[192];
  ui::uiBuildContextLine(&snapshot, line, sizeof(line));
  CHECK(std::strstr(line, "ВЫБРАНО") != nullptr);
  CHECK(std::strstr(line, "ФЕЙД") != nullptr);
  CHECK(std::strstr(line, "МИК") != nullptr);
  setLanguage(Lang::En);
  INFO("i18n: RU context line uses localized SELECTED/FADERS/MIC");
}

TEST(I18nProjectV2PersistsLanguage) {
  setLanguage(Lang::En);
  Sequencer seq;
  seq.init(48000.0f);
  storage::ProjectV2 project;
  storage::captureProjectV2(seq, &project);
  CHECK(project.language == static_cast<uint8_t>(Lang::En));
  std::vector<uint8_t> bytes(storage::projectV2SerializedSize(project));
  CHECK(storage::projectV2Serialize(project, bytes.data(), bytes.size()) > 0);
  setLanguage(Lang::Ru);
  storage::ProjectV2 loaded;
  CHECK(storage::projectV2Deserialize(bytes.data(), bytes.size(), &loaded));
  CHECK(loaded.language == static_cast<uint8_t>(Lang::En));
  setLanguage(Lang::En);
  INFO("project v2: language field roundtrips (EN saved; global switch not implicit)");
}

TEST(I18nProjectV2V1MigrationRussian) {
  Sequencer seq;
  seq.init(48000.0f);
  storage::Project old;
  storage::captureProject(seq, &old);
  const char* path = "../tests/out/i18n_v1_migration.bkfp";
  CHECK(storage::projectSaveFile(old, path));
  storage::ProjectV2 migrated;
  CHECK(storage::projectV2Load(path, &migrated));
  CHECK(migrated.language == static_cast<uint8_t>(Lang::Ru));
  std::remove(path);
  INFO("project v2: v1 files migrate with language=RU");
}

TEST(I18nRendersBothLanguages) {
  setLanguage(Lang::En);
  ui::UiSnapshot en;
  ui::uiSnapshotDemo(&en, ui::Screen::Main);
  ui::Framebuffer800 enFb;
  ui::drawUi800(enFb, en);
  setLanguage(Lang::Ru);
  ui::UiSnapshot ru;
  ui::uiSnapshotDemo(&ru, ui::Screen::Main);
  ui::Framebuffer800 ruFb;
  ui::drawUi800(ruFb, ru);
  CHECK(nonBlack(enFb) > 2000);
  CHECK(nonBlack(ruFb) > 2000);
  CHECK(checksum(enFb) != checksum(ruFb));
  setLanguage(Lang::En);
  INFO("i18n: UI renders in both EN and RU (distinct frames)");
}

TEST(I18nMicExtGenLocalized) {
  setLanguage(Lang::Ru);
  ui::UiSnapshot mic;
  ui::uiSnapshotMicDemo(&mic);
  CHECK(std::strcmp(mic.params[0].label, "ИСТОЧНИК") == 0);
  ui::UiSnapshot ext;
  ui::uiSnapshotExtDemo(&ext);
  CHECK(std::strcmp(ext.params[0].label, "КАН") == 0);
  ui::UiSnapshot gen;
  ui::uiSnapshotGenDemo(&gen);
  CHECK(std::strcmp(gen.params[0].label, "ВЕРОЯТ") == 0);
  setLanguage(Lang::En);
  INFO("i18n: MIC/EXT/GEN pages localize labels in RU");
}
