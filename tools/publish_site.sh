#!/usr/bin/env bash
# Публикация сайта в ветку gh-pages из каталога docs/ (без изменения рабочего дерева).
set -euo pipefail
cd "$(dirname "$0")/.."
TMP=$(mktemp -d); IDX=$(mktemp)
trap 'rm -rf "$TMP" "$IDX"' EXIT
cp -R docs/index.html docs/en docs/assets docs/sitemap.xml docs/robots.txt docs/llms.txt "$TMP"/
[ -f docs/.nojekyll ] && cp docs/.nojekyll "$TMP"/.nojekyll
GIT_INDEX_FILE="$IDX" git read-tree --empty
GIT_INDEX_FILE="$IDX" git --work-tree="$TMP" add -A -- .
tree=$(GIT_INDEX_FILE="$IDX" git write-tree)
commit=$(git commit-tree "$tree" -m "site: publish $(cat VERSION) from docs/")
git branch -f gh-pages "$commit"
git push --force origin gh-pages
echo "Опубликовано: https://martiyanov.github.io/bukifon/ (commit $commit)"
