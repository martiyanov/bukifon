#!/usr/bin/env bash
# Проверка целостности release bundle: SHA256SUMS + обязательные файлы + отсутствие PII.
# Использование: bash tools/verify_release_bundle.sh [dist/release-vX.Y.Z]
set -uo pipefail
cd "$(dirname "$0")/.."
DIR=${1:-$(ls -d dist/release-v* 2>/dev/null | sort -V | tail -1)}
if [ -z "${DIR:-}" ] || [ ! -d "$DIR" ]; then echo "bundle не найден: $DIR"; exit 2; fi
echo "проверка: $DIR"
fail=0
if [ -f "$DIR/SHA256SUMS" ]; then
  (cd "$DIR" && (shasum -a 256 -c SHA256SUMS 2>/dev/null || sha256sum -c SHA256SUMS 2>/dev/null) | grep -v ': OK$' | tail -5) || true
  bad=$(cd "$DIR" && (shasum -a 256 -c SHA256SUMS 2>/dev/null || sha256sum -c SHA256SUMS 2>/dev/null) | grep -vc ': OK$')
  echo "SHA256SUMS: нарушений ${bad:-?}"
  [ "${bad:-1}" = "0" ] || fail=1
else
  echo "SHA256SUMS отсутствует"; fail=1
fi
for f in README.txt VERSION CHANGELOG.md MANIFEST.md SHA256SUMS licenses/LICENSE licenses/NOTICE SBOM.txt RELEASE_BUNDLE.md; do
  [ -e "$DIR/$f" ] || [ -e "$DIR/licenses/$f" ] || { echo "нет: $f"; fail=1; }
done
# PII/абсолютные домашние пути
if grep -rIl --exclude-dir=.git --exclude='SHA256SUMS' -E '/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/' "$DIR" 2>/dev/null | head -3 | grep -q .; then
  echo "найдены абсолютные домашние пути"; fail=1
fi
echo "PII: $([ "$fail" = 0 ] && echo ok || echo проблемы)"
echo "ИТОГ: $([ "$fail" = 0 ] && echo ✅ bundle целостен || echo ❌ есть проблемы)"
exit $fail
