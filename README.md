
# WCA Regulations Compiler

This is a tool to check, build, compare WCA Regulations and Guidelines and its translations.

## Install from PyPi

Just run `pip install wrc`.

## External dependencies

If you want to build the pdf versions, you need the **patched qt** version of [wkhtmltopdf](http://wkhtmltopdf.org/) in your `$PATH`.
These stable standalone binaries are available [here](http://wkhtmltopdf.org/downloads.html) for several platforms.

For CJK translations you also need to install some packages providing CJK fonts. The official build uses "UnBatang" for Korean (package `fonts-unfonts-core` or alike), "WenQuanYi Micro Hei" for Chinese (package `fonts-wqy-microhei` or alike), and "IPAX0208PGothic" for Japanese (package `fonts-ipafont` or alike).

## Run the thing

Here are some sample invocations:

- To check the Regulations and Guidelines:
`wrc path/to/wca-regulations --target=check`
- To build the html to the `build` directory:
`wrc path/to/wca-regulations --target=html --output=build`
- To merge the Regulations and Guidelines into a single document (works with html, pdf and json targets):
`wrc path/to/wca-regulations --target=html --output=build --merged`
- When building translation it's necessary to provide the language (to choose the appropriate font/pdf names):
`wrc path/to/wca-regulations-translations/french --language=french --target=pdf --output=build`
- Check that a translation matches exactly the original rules:
`wrc path/to/wca-regulations-translations/french --diff=path/to/wca-regulations`

You can also take a look at the travis [script](https://github.com/thewca/wca-regulations-translations/blob/master/travis.sh) used in the translations repository.

## Translating through a catalog

A translation can be kept as a set of strings instead of a second copy of the
document. The document already numbers its own rules, and `--diff` already
treats those numbers as the identity of a rule across languages, so they are
what the strings are keyed on.

- Extract the translatable strings from English:
`wrc path/to/wca-regulations.md --target=pot --output=build`
- Convert a translation that is still a checked-in document into a catalog:
`wrc-bootstrap path/to/wca-regulations.md path/to/wca-regulations-translations/japanese -o japanese.po -l ja`

`--po` then applies to **every** target. The strings are swapped on the parsed
English before any backend runs, so there is no separate translated document to
build from -- the published formats come straight out of English plus a
catalog:

```
wrc wca-regulations.md --target=html     --po=japanese.po --output=build
wrc wca-regulations.md --target=json     --po=japanese.po --output=build
wrc wca-regulations.md --target=pdf      --po=japanese.po --language=japanese --output=build
wrc wca-regulations.md --target=markdown --po=japanese.po --output=build
```

`--language` still picks the font and pdf filename, so it is needed for `pdf`
as before; the other targets do not read it. `--target=markdown` writes the
source format back out, which is what the translations repository holds today.

The skeleton always comes from the English document, so a translation has the
same articles and the same rules in the same order no matter how far behind the
catalog is. Untranslated strings come out in English rather than going missing,
which is why building English through its own (empty) template reproduces the
input:

```
wrc wca-regulations.md --target=pot --output=build
wrc wca-regulations.md --target=markdown --po=build/wca-regulations.pot --output=build
diff wca-regulations.md build/wca-regulations.md
```

The markdown backend puts a blank line after every heading, so that diff
reports the five headings in `## Notes` that do not currently have one.
Normalising those in the source makes the round trip exact; it is already exact
for anything the backend has produced.

### Getting the catalogs onto a translation platform

`./catalogs.sh` builds the whole set at once, named by language code rather
than by the English language name the translations repository uses as a
directory:

```
./catalogs.sh wca-regulations.md ../wca-regulations-translations catalogs
```

`./seed-weblate.sh catalogs` then creates a Weblate component from them, and
the **Seed Weblate** workflow does both against the repositories on GitHub. It
is `workflow_dispatch` only and needs two secrets, `WEBLATE_URL` and
`WEBLATE_TOKEN`.

Both the script and the workflow only *create* a component. Re-running against
one that already exists would have to either overwrite whatever translators had
done since or silently do nothing, so it refuses instead. Keeping a component
up to date after the English changes is a msgmerge:

```
wrc wca-regulations.md --target=pot --output=catalogs
msgmerge --update --backup=none catalogs/ja.po catalogs/wca-regulations.pot
```

Two things are worth knowing before pointing translators at this:

- Guideline labels are translated (the Dutch document tags its guidelines
  `[AANVULLING]`, not `[ADDITION]`), so each label is two strings, keyed on the
  English name. The label in front of a guideline is rendered from that pair,
  not retyped by the translator.
- `doc:version` is a whole version line, date included. Splitting the wording
  from the date would be better, but the lexer does not take them apart today.


## Running from the sources

The compiler is built on top of python lex/yacc implementation `ply`, so you probably need to run `pip install ply` to install it.
When this is done, you can use `python -m wrc.wrc` from the repository's root instead of `wrc`.
If you want to use `wrc-states` from the source, an easy way to do this is to run `python -c "from wrc.wrc import states; states()"`

## Deploying to PyPi

(section for maintainers in PyPi)

- Bump the version number in `wrc/version.py` and in `pyproject-toml`
- (optional, depends on your environment) `pip install --upgrade build`
- `python -m build`
- `twine upload dist/*`
