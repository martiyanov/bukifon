#!/usr/bin/env bash
# Сборка кандидата v1.0-rc: release bundle + fresh-history bundle + проверки + чек-лист.
# Использование: bash tools/make_rc_bundle.sh [--dry-run]
set -uo pipefail
cd "$(dirname "$0")/.."
DRY=""
[ "${1:-}" = "--dry-run" ] && DRY=echo
V=$(cat VERSION)
echo "== VERSION $V"
if ! grep -q "\[$V\]" CHANGELOG.md; then echo "FAIL: VERSION нет в CHANGELOG"; exit 1; fi
if ! grep -q "$V" README.md; then echo "FAIL: VERSION нет в README"; exit 1; fi

echo "== проверки"
$DRY bash tools/check_all.sh >/tmp/rc_check_all.log 2>&1 || { tail -5 /tmp/rc_check_all.log; echo "FAIL: check_all"; exit 1; }
$DRY bash tools/security_scan.sh >/tmp/rc_security.log 2>&1 || { tail -5 /tmp/rc_security.log; echo "FAIL: security"; exit 1; }
tail -1 /tmp/rc_check_all.log 2>/dev/null; tail -1 /tmp/rc_security.log 2>/dev/null

echo "== bundle"
$DRY bash tools/make_release_bundle.sh >/tmp/rc_bundle.log 2>&1 || { tail -5 /tmp/rc_bundle.log; echo "FAIL: bundle"; exit 1; }
tail -2 /tmp/rc_bundle.log
$DRY bash tools/verify_release_bundle.sh "$(ls -d dist/release-v$V 2>/dev/null | tail -1)" || echo "warn: verify (bundle ещё не создан — dry-run)"

echo "== fresh history"
$DRY bash tools/fresh_history_push.sh >/tmp/rc_fresh.log 2>&1 || { tail -5 /tmp/rc_fresh.log; echo "FAIL: fresh"; exit 1; }
tail -2 /tmp/rc_fresh.log

echo
echo "== чек-лист RC (docs/87)"
cat <<TXT
- [ ] PWR 13/13 PASS (docs/51, tools/pwr_bench_check.py --strict)
- [ ] P1: P4-vs-H743 (docs/56), MCU freeze (spec/90)
- [ ] PCB rev.1: DRC/DFM 0, fab-пакет проверен (tools/check_fab_package.py)
- [ ] 3–5 прототипов, self-test 21/21, bring-up 15 шагов (docs/80)
- [ ] UX blind-тест 5 людей (docs/74), time-to-sound ≤10 c
- [ ] recovery/серийники/прошивка проверены (docs/42/55)
- [ ] release notes v1.0-rc (docs/87), тег v1.0.0-rc.1
TXT
echo "готово: dist/release-v$V, dist/bukifon-fresh-v$V.bundle"
