#!/usr/bin/env bash
#
# Build the translation catalogs for every language in
# wca-regulations-translations, named the way a translation platform expects.
#
#   ./catalogs.sh path/to/wca-regulations.md path/to/wca-regulations-translations catalogs
#
# Produces
#   catalogs/wca-regulations.pot   the strings to translate, from English
#   catalogs/<code>.po             one catalog per language
#
# The translations repository names its directories after the language in
# English ("portuguese-brazilian"); the files here are named with the language
# code instead, because that is what a platform matches a translation on.
set -euo pipefail

REFERENCE="${1:?usage: $0 <english wca-regulations.md> <translations dir> <output dir>}"
TRANSLATIONS="${2:?usage: $0 <english wca-regulations.md> <translations dir> <output dir>}"
OUTPUT="${3:?usage: $0 <english wca-regulations.md> <translations dir> <output dir>}"

# Kept here rather than in data/languages.json because that file is fetched
# from the compiler's main branch at run time, so a local edit to it would be
# ignored until it is merged and deployed.
CODES="
belarusian be
chinese zh_Hans
chinese-traditional zh_Hant
croatian hr
dutch nl
finnish fi
french fr
german de
hungarian hu
indonesian id
italian it
japanese ja
kazakh kk
korean ko
polish pl
portuguese-brazilian pt_BR
portuguese-european pt
russian ru
slovenian sl
spanish-american es_419
spanish-european es
swedish sv
thai th
ukrainian uk
vietnamese vi
"

mkdir -p "$OUTPUT"

echo "==> Template"
# wrc reports its errors on stdout, so they have to be held and shown rather
# than sent to /dev/null along with the progress chatter.
wrc "$REFERENCE" --target=pot --output="$OUTPUT" > "$OUTPUT/.wrc.log" 2>&1 || {
  sed 's|^|    |' "$OUTPUT/.wrc.log" >&2
  echo "    (the input has to be named wca-regulations.md; wrc detects the" >&2
  echo "     document from the filename)" >&2
  rm -f "$OUTPUT/.wrc.log"
  exit 1
}
rm -f "$OUTPUT/.wrc.log"
echo "    $OUTPUT/wca-regulations.pot ($(grep -c '^msgctxt' "$OUTPUT/wca-regulations.pot") strings)"

echo "==> Catalogs"
missing=0
while read -r language code; do
  [ -n "$language" ] || continue
  if [ ! -d "$TRANSLATIONS/$language" ]; then
    echo "    $language: no such directory, skipped" >&2
    missing=1
    continue
  fi
  wrc-bootstrap "$REFERENCE" "$TRANSLATIONS/$language" \
    -o "$OUTPUT/$code.po" -l "$code" | sed 's|^|    |'
done <<< "$CODES"

# msgfmt is not required to build the catalogs, but it is the same check the
# platform will apply on import, so it is worth failing here instead of there.
if command -v msgfmt > /dev/null; then
  echo "==> Checking"
  for catalog in "$OUTPUT"/*.po; do
    msgfmt --check-format --check-domain -o /dev/null "$catalog" \
      || { echo "    $catalog is not valid gettext" >&2; exit 1; }
  done
  echo "    all catalogs are valid gettext"
fi

exit $missing
