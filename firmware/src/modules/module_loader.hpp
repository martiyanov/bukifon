// SPDX-License-Identifier: GPL-3.0-or-later
// Module SDK v0.2 loader: manifest validation + SHA-256/size/API/ABI checks.
// Nothing is executed before the manifest is fully valid; invalid modules are
// rejected and never appear in the installed list.
#pragma once

#include <cstddef>
#include <cstdint>

#include "modules/module_manifest.hpp"

namespace bukifon {

constexpr int kMaxInstalledModules = 16;

struct InstalledModule {
  char id[64] = {};
  char version[16] = {};
  char sha256[65] = {};
  uint32_t size = 0;
  uint32_t permissions = 0;
};

class ModuleLoader {
 public:
  void clear();
  // Load one module from manifest JSON + DSP payload.  Returns false and never
  // installs/executes anything when validation fails.
  bool load(const char* manifestJson, const uint8_t* payload, size_t payloadSize,
            char* error, size_t errorLen);
  // Same, reading both files (host tools/tests).
  bool loadFiles(const char* manifestPath, const char* dspPath, char* error,
                 size_t errorLen);

  int count() const { return count_; }
  const InstalledModule* at(int index) const;
  const InstalledModule* find(const char* id) const;
  bool installed(const char* id) const { return find(id) != nullptr; }

  uint32_t attempts() const { return attempts_; }
  uint32_t rejected() const { return rejected_; }
  bool executedAnything() const { return executedAnything_; }
  const char* lastError() const { return lastError_; }

 private:
  InstalledModule modules_[kMaxInstalledModules];
  int count_ = 0;
  uint32_t attempts_ = 0;
  uint32_t rejected_ = 0;
  bool executedAnything_ = false;
  char lastError_[192] = {};
};

}  // namespace bukifon
