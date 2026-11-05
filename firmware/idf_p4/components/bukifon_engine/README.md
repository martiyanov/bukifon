# bukifon_engine (ESP-IDF component scaffold)

Header-only/empty by default, so the hello project builds without the engine.
Copy the portable engine sources here to build them as an IDF component:

```bash
cd firmware/idf_p4/components/bukifon_engine
cp ../../../engine_unity.cpp .
mkdir -p src include
cp -R ../../../src/. src/
cp -R ../../../include/. include/
```

`CMakeLists.txt` picks `src/**/*.cpp` if present, otherwise `engine_unity.cpp`.
Add `REQUIRES bukifon_engine` to `main/CMakeLists.txt` and include headers such
as `#include "audio/engine.hpp"`.

Do **not** copy `firmware/src/hal` (Arduino-only).  IDF drivers replace it:
`driver/i2c_master`, `driver/i2s_std`, `esp_lcd`, `sdmmc`, `esp_tinyusb`.
