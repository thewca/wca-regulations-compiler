#!/usr/bin/env bash
#
# Creates a Weblate component from catalogs built by ./catalogs.sh.
#
#   WEBLATE_URL=https://translate.worldcubeassociation.org \
#   WEBLATE_TOKEN=wlu_xxx \
#     ./seed-weblate.sh catalogs
#
# The token comes from Weblate under /accounts/profile/#api. Against a local
# stack, the admin's is:
#
#   docker compose exec -T weblate weblate shell <<'PY'
#   from weblate.auth.models import User
#   from rest_framework.authtoken.models import Token
#   print(Token.objects.get_or_create(user=User.objects.get(username="admin"))[0].key)
#   PY
#
# The catalogs are gettext PO keyed on the rule numbers the Regulations already
# use, so `context:r"^2"` in Weblate is every rule in Article 2 and nothing
# else. They are generated rather than checked in, so there is no repository
# for Weblate to track: this uses Weblate's own local VCS and ships the
# catalogs in as a zip when the component is created.
set -euo pipefail

CATALOGS="${1:?usage: $0 <catalog directory>}"
WEBLATE_URL="${WEBLATE_URL:?set WEBLATE_URL, e.g. https://translate.worldcubeassociation.org}"
WEBLATE_TOKEN="${WEBLATE_TOKEN:?set WEBLATE_TOKEN to an API token that can create components}"
PROJECT="${PROJECT:-wca}"
SLUG="${SLUG:-regulations}"
# Weblate requires the display name to be unique within the project too, so it
# has to move whenever SLUG does.
NAME="${NAME:-Regulations}"

WEBLATE_URL="${WEBLATE_URL%/}"

[ -f "$CATALOGS/wca-regulations.pot" ] || {
  echo "No wca-regulations.pot in ${CATALOGS}. Build the catalogs first:" >&2
  echo "  ./catalogs.sh wca-regulations.md ../wca-regulations-translations ${CATALOGS}" >&2
  exit 1
}

# Status is checked explicitly rather than relying on `curl -f`, which only
# fails on 4xx/5xx: a redirect exits 0 with an empty body, so a misconfigured
# URL would look like it succeeded while creating nothing.
request() {
  local method="$1" path="$2"; shift 2
  local body code
  body="$(mktemp)"
  # `|| true` rather than `|| echo 000`: curl -w already prints 000 when it
  # cannot connect *and* exits non-zero, so echoing as well appended a second
  # one and the code came out as "000000", matching no case below.
  code="$(curl -sS -o "$body" -w '%{http_code}' -X "$method" "${WEBLATE_URL}/api${path}" \
    -H "Authorization: Token ${WEBLATE_TOKEN}" "$@" 2>/dev/null || true)"
  [ -n "$code" ] || code=000
  case "$code" in
    2*) rm -f "$body"; return 0 ;;
    000)
      rm -f "$body"
      echo "Could not reach ${WEBLATE_URL}." >&2
      return 1
      ;;
    3*)
      rm -f "$body"
      echo "Weblate redirected ${method} ${path} (HTTP ${code})." >&2
      echo "WEBLATE_URL should be the https:// address, with no trailing path." >&2
      return 1
      ;;
    401|403)
      rm -f "$body"
      echo "Weblate rejected the token on ${method} ${path} (HTTP ${code})." >&2
      echo "It has to belong to an account that can create components in '${PROJECT}'." >&2
      return 1
      ;;
    *) sed 's/^/    /' "$body" >&2; rm -f "$body"; return 1 ;;
  esac
}

exists() {
  local code
  code="$(curl -sS -o /dev/null -w '%{http_code}' \
    -H "Authorization: Token ${WEBLATE_TOKEN}" "${WEBLATE_URL}/api$1" 2>/dev/null || true)"
  [ "$code" = "200" ]
}

echo "==> ${WEBLATE_URL}, project '${PROJECT}'"

# Check the token up front. Without this a token that cannot read comes back as
# "component does not exist" from every check below, and the run gets as far as
# trying to create things before saying anything useful.
request GET /projects/ > /dev/null

# Re-running would have to either clobber whatever translators have done since
# the last run or silently do nothing, and neither is a good default. Updating
# after the English changes is a msgmerge, not a re-seed -- see the note at the
# end of this script.
if exists "/components/${PROJECT}/${SLUG}/"; then
  echo "Component '${SLUG}' already exists: ${WEBLATE_URL}/projects/${PROJECT}/${SLUG}/" >&2
  echo "This script only creates it. Delete it under Manage -> Settings to start" >&2
  echo "over, or set SLUG and NAME to seed a second copy alongside it." >&2
  exit 1
fi

if ! exists "/projects/${PROJECT}/"; then
  echo "==> Creating project '${PROJECT}'"
  request POST /projects/ \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"WCA\",\"slug\":\"${PROJECT}\",\"web\":\"https://www.worldcubeassociation.org/\"}"
fi

# The zip is laid out as regulations/*.po so it matches the filemask once
# Weblate unpacks it into the local repository.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/regulations"
cp "$CATALOGS"/*.po "$CATALOGS"/wca-regulations.pot "$TMP/regulations/"
(cd "$TMP" && zip -qr catalogs.zip regulations)
echo "==> Packed $(ls "$CATALOGS"/*.po | wc -l | tr -d ' ') catalogs"

# file_format MUST be "po", not "po-mono". These catalogs are bilingual: the
# msgid is the English rule and the msgstr is the translation, which is what
# lets Weblate mark a translation as needing work when the English is reworded.
# po-mono would treat the rule number as the string and lose that entirely.
#
# docfile= does not work here: Weblate takes an uploaded document as the
# monolingual base file and then rejects it with "You can not use a base file
# for bilingual translation". zipfile= is the route that seeds a local repo.
echo "==> Creating component '${SLUG}'"
request POST "/projects/${PROJECT}/components/" \
  -F name="${NAME}" \
  -F slug="${SLUG}" \
  -F vcs=local \
  -F repo=local: \
  -F file_format=po \
  -F filemask='regulations/*.po' \
  -F new_base='regulations/wca-regulations.pot' \
  -F new_lang=add \
  -F language_code_style=linux \
  -F license="GPL-3.0-or-later" \
  -F zipfile=@"$TMP/catalogs.zip"

cat <<EOF

Done. Weblate scans the catalogs in the background; the per-language counts
take about half a minute to appear.

  ${WEBLATE_URL}/projects/${PROJECT}/${SLUG}/

Because the strings are keyed on rule numbers, the search box filters by
article without anyone needing to know a directory layout:

  context:r"^2"                     every rule in Article 2
  context:r"^A" AND state:empty     Article A, not yet translated
  context:="2i2a"                   one specific rule
  context:r"^(article|label|doc):"  headings, labels and the version line

When the English Regulations change this is a msgmerge, not a re-seed: pull the
catalogs back out of Weblate, merge the new template into them and push them
back, so reworded rules come back as needing work instead of quietly staying on
the old translation.

  wrc wca-regulations.md --target=pot --output=catalogs
  msgmerge --update --backup=none catalogs/ja.po catalogs/wca-regulations.pot
EOF
