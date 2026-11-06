// SPDX-License-Identifier: GPL-3.0-or-later
#include "nvs_storage_backend.hpp"

#include <cstring>

#if defined(CONFIG_IDF_TARGET_ESP32P4)
#include "esp_err.h"
#include "nvs.h"
#include "nvs_flash.h"
#endif

namespace bukifon {

#if defined(CONFIG_IDF_TARGET_ESP32P4)

static bool openNs(const char* ns, nvs_open_mode_t mode, nvs_handle_t* handle) {
  if (!handle) return false;
  const char* name = (ns && ns[0]) ? ns : NvsStorageBackend::kDefaultNamespace;
  return nvs_open(name, mode, handle) == ESP_OK;
}

bool NvsStorageBackend::begin() {
  nvs_stats_t stats = {};
  if (nvs_get_stats(nullptr, &stats) != ESP_OK) return false;
  freeEntries_ = static_cast<uint32_t>(stats.free_entries);
  usedEntries_ = static_cast<uint32_t>(stats.used_entries);
  return true;
}

bool NvsStorageBackend::write(const char* ns, const char* key, const uint8_t* data,
                              size_t size) {
  if (!key || !data) return false;
  nvs_handle_t handle;
  if (!openNs(ns, NVS_READWRITE, &handle)) return false;
  const esp_err_t rc = nvs_set_blob(handle, key, data, size);
  const esp_err_t commit = rc == ESP_OK ? nvs_commit(handle) : rc;
  nvs_close(handle);
  return commit == ESP_OK;
}

bool NvsStorageBackend::read(const char* ns, const char* key, uint8_t* out, size_t capacity,
                             size_t* outSize) const {
  if (outSize) *outSize = 0;
  if (!key || !out) return false;
  nvs_handle_t handle;
  if (!openNs(ns, NVS_READONLY, &handle)) return false;
  size_t size = capacity;
  const esp_err_t rc = nvs_get_blob(handle, key, out, &size);
  nvs_close(handle);
  if (rc != ESP_OK) return false;
  if (outSize) *outSize = size;
  return true;
}

bool NvsStorageBackend::erase(const char* ns, const char* key) {
  if (!key) return false;
  nvs_handle_t handle;
  if (!openNs(ns, NVS_READWRITE, &handle)) return false;
  esp_err_t rc = nvs_erase_key(handle, key);
  if (rc == ESP_ERR_NVS_NOT_FOUND) rc = ESP_OK;
  if (rc == ESP_OK) rc = nvs_commit(handle);
  nvs_close(handle);
  return rc == ESP_OK;
}

bool NvsStorageBackend::exists(const char* ns, const char* key) const {
  return size(ns, key) > 0;
}

size_t NvsStorageBackend::size(const char* ns, const char* key) const {
  if (!key) return 0;
  nvs_handle_t handle;
  if (!openNs(ns, NVS_READONLY, &handle)) return 0;
  size_t size = 0;
  const esp_err_t rc = nvs_get_blob(handle, key, nullptr, &size);
  nvs_close(handle);
  return rc == ESP_OK ? size : 0;
}

#else

bool NvsStorageBackend::begin() { return false; }
bool NvsStorageBackend::write(const char*, const char*, const uint8_t*, size_t) { return false; }
bool NvsStorageBackend::read(const char*, const char*, uint8_t*, size_t, size_t*) const {
  return false;
}
bool NvsStorageBackend::erase(const char*, const char*) { return false; }
bool NvsStorageBackend::exists(const char*, const char*) const { return false; }
size_t NvsStorageBackend::size(const char*, const char*) const { return 0; }

#endif

}  // namespace bukifon
