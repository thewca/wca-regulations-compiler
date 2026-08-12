'''
Turn a checked-in translation into a catalog, once.

The translations in wca-regulations-translations are whole copies of the
document, so moving to catalogs would throw the work away unless the existing
text is matched up to the English it translates first. Most of it matches on an
identifier that is the same in every language: rule numbers, article numbers,
`doc:` keys. Headings and label names are themselves translated and have no
such identifier, so those few are matched on their position in the document,
which every translation has kept.

This is a migration tool. Once a language is in Weblate, the catalog is the
source and the markdown is generated from it.
'''
import argparse
import os
import sys

import polib

from .codegen.cgpot import HEADER, WCADocumentPot
from .wrc import (GUIDELINES_FILENAME, REGULATIONS_FILENAME,
                  parse_regulations_guidelines)

# Keys that mean the same thing in every language, so they can be matched
# directly. Everything else is matched on position.
STABLE_PREFIXES = ('doc:', 'article:')


def kind_of(key):
    ''' How an entry has to be matched up: by key, or by position and kind. '''
    if key.startswith(STABLE_PREFIXES):
        return None
    if key.startswith('label:'):
        return 'label'
    if ':' in key:
        return 'heading'
    # A bare key is a rule number, which is the identity of a rule everywhere.
    return None


def index(entries):
    ''' Split entries into a by-key lookup and a by-position-within-kind one. '''
    by_key = {}
    by_position = {}
    counts = {}
    for key, source, _ in entries:
        kind = kind_of(key)
        if kind is None:
            # First one wins. A pre-merge translation is two documents, and
            # both of them define doc:title and a heading for every article;
            # the Regulations are parsed first and are the ones we want.
            by_key.setdefault(key, source)
        else:
            position = counts.get(kind, 0)
            by_position[(kind, position)] = source
            counts[kind] = position + 1
    return by_key, by_position, counts


def documents(path):
    '''
    The Regulations and Guidelines under `path`, either of which may be absent.

    Unlike the build targets, this accepts a directory holding only one of the
    two: the languages that have kept up with the July 2025 merge have dropped
    wca-guidelines.md, while the ones that have not still carry both.
    '''
    if os.path.isfile(path):
        if path.endswith(GUIDELINES_FILENAME):
            return None, path
        return path, None
    found = tuple(os.path.join(path, name) if os.path.isfile(os.path.join(path, name))
                  else None
                  for name in (REGULATIONS_FILENAME, GUIDELINES_FILENAME))
    if not any(found):
        print("Error: '%s' holds neither %s nor %s."
              % (path, REGULATIONS_FILENAME, GUIDELINES_FILENAME))
        sys.exit(1)
    return found


def extract(document):
    ''' Every translatable string of a parsed document, in order. '''
    reg, guide, errors, warnings = parse_regulations_guidelines(*documents(document))
    if errors or warnings:
        for message in errors + warnings:
            print(" - " + message)
        sys.exit(1)
    return WCADocumentPot('', '', '').entries(reg, guide)


def run():
    argparser = argparse.ArgumentParser(
        description='Build a translation catalog from a checked-in translation')
    argparser.add_argument('reference', help='The English document or its directory')
    argparser.add_argument('input', help='The translation directory')
    argparser.add_argument('-o', '--output', required=True, help='Catalog to write')
    argparser.add_argument('-l', '--language', default='',
                           help='Language code to record in the catalog')
    options = argparser.parse_args()

    english = extract(options.reference)
    _, _, english_counts = index(english)
    by_key, by_position, counts = index(extract(options.input))

    # Position is only trustworthy when the two documents have the same number
    # of headings, or of labels, to line up. A language that has not followed
    # the July 2025 merge has a heading for every one of its two documents and
    # would otherwise get its Contents heading filed under Labels. Leaving those
    # few strings for a translator beats guessing wrong and looking translated.
    aligned = set()
    for kind, count in english_counts.items():
        if counts.get(kind) == count:
            aligned.add(kind)
        else:
            print("Not carrying over %s strings: %d here, %d in the translation"
                  % (kind, count, counts.get(kind, 0)))

    catalog = polib.POFile(check_for_duplicates=True)
    catalog.metadata = dict(HEADER, Language=options.language)
    seen = {}
    for key, source, comment in english:
        kind = kind_of(key)
        if kind is None:
            translated = by_key.get(key, '')
        else:
            position = seen.get(kind, 0)
            seen[kind] = position + 1
            translated = by_position.get((kind, position), '') if kind in aligned else ''
        # A translation identical to the English is text nobody has translated
        # yet, not a translation that happens to agree.
        if translated == source:
            translated = ''
        catalog.append(polib.POEntry(msgctxt=key, msgid=source, msgstr=translated,
                                     comment=comment))
    catalog.save(options.output)

    translated = len(catalog.translated_entries())
    print("%s: %d of %d strings carried over (%.1f%%)"
          % (options.output, translated, len(catalog),
             100.0 * translated / len(catalog)))


if __name__ == '__main__':
    run()
