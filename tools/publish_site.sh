#!/usr/bin/env bash
# Публикация сайта в ветку gh-pages из каталога docs/.
# Использование: bash tools/publish_site.sh
set -euo pipefail
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cp -R docs/index.html docs/en docs/assets docs/sitemap.xml docs/robots.txt docs/llms.txt "$TMP"/
[ -f docs/.nojekyll ] && cp docs/.nojekyll "$TMP"/.nojekyll
git read-tree --empty
git --work-tree="$TMP" add -A -- .
tree=$(git write-tree)
commit=$(git commit-tree "$tree" -m "site: publish $(cat VERSION) from docs/")
git branch -f gh-pages "$commit"
git reset -q --hard HEAD
git push --force origin gh-pages
echo "Опубликовано: https://martiyanov.github.io/bukifon/ (commit $commit)"
