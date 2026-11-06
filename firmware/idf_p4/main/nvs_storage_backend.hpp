// SPDX-License-Identifier: GPL-3.0-or-later
// Real ESP-IDF NVS adapter for the P4 bring-up app (docs/42 §9/§10).
// Same read/write/erase/exists/size surface as the host StorageBackend, but
// backed by nvs_flash with the `bukifon` namespace.  Host tests use
// firmware/src/storage/storage_backend.* instead; this file is compiled only
// for CONFIG_IDF_TARGET_ESP32P4.
#pragma once

#include <cstddef>
#include <cstdint>

#if defined(CONFIG_IDF_TARGET_ESP32P4)
#include "nvs.h"
#include "nvs_flash.h"
#endif

namespace bukifon {

class NvsStorageBackend {
 public:
  static constexpr const char* kDefaultNamespace = "bukifon";

  bool begin();
  bool write(const char* ns, const char* key, const uint8_t* data, size_t size);
  bool read(const char* ns, const char* key, uint8_t* out, size_t capacity,
            size_t* outSize) const;
  bool erase(const char* ns, const char* key);
  bool exists(const char* ns, const char* key) const;
  size_t size(const char* ns, const char* key) const;
  const char* name() const { return "nvs"; }
  uint32_t freeEntries() const { return freeEntries_; }
  uint32_t usedEntries() const { return usedEntries_; }

 private:
  uint32_t freeEntries_ = 0;
  uint32_t usedEntries_ = 0;
};

}  // namespace bukifon
