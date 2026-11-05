// SPDX-License-Identifier: GPL-3.0-or-later
// Writes the UAC2 8x8 HS descriptor JSON dump for the USB analyser comparison.
#include <cstdio>

#include "usb/uac2_8x8.hpp"

int main() {
  bukifon::usb::Uac2_8x8Builder builder;
  builder.setVidPid(0x1209, 0x0001);
  if (!builder.build()) {
    std::fprintf(stderr, "UAC2 descriptor build failed\n");
    return 1;
  }
  const auto& d = builder.descriptors();
  if (!builder.writeJson("../artifacts/usb/uac2_8x8.json")) {
    std::fprintf(stderr, "cannot write ../artifacts/usb/uac2_8x8.json\n");
    return 1;
  }
  std::printf("UAC2 8x8 HS: config=%u B, interfaces=%u, endpoints=%u, budget=%d/%d (%s)\n",
              d.configTotalLength, d.interfaces, d.endpoints, d.budget.total(), d.budget.limit,
              d.budget.fits() ? "fits" : "OVERFLOW");
  std::printf("artifact: ../artifacts/usb/uac2_8x8.json\n");
  return d.budget.fits() ? 0 : 2;
}
