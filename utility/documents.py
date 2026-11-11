"""Markdown documents from `docs/`, read once and rendered where they belong.

Three pages show prose that lives in a file rather than in code: the home page (the
introduction and the release notes) and the ladder (how the rating works). Reading,
splitting the `# ` title off and choosing the heading level are the same in all of
them, so they live here.

The files are small and edited by hand, so nothing is cached: an edit shows up on the
next rerun. `utf-8-sig` strips a BOM if an editor wrote one and behaves exactly like
`utf-8` when it did not.
"""

from pathlib import Path

import streamlit as st

from utility.methods import error

DOCS = Path('docs')
PATCH_NOTES = DOCS / 'patch-notes'

def read_document(path):
    """A doc file -> (title, body). The first `# ` line is the title."""
    text = path.read_text(encoding='utf-8-sig')
    heading, _, body = text.partition('\n')
    if heading.startswith('# '):
        return heading[2:].strip(), body.strip()
    return path.stem, text.strip()

def note_key(path):
    """Sort key for `YYYY-MM-DD-<version>-<slug>.md`, compared as date then version."""
    date = path.stem[:10]
    version = path.stem[11:].split('-', 1)[0]
    return (date, tuple(int(part) for part in version.split('.') if part.isdigit()))

def patch_note_paths():
    """Release notes, newest first. Empty when the folder is missing or bare."""
    if not PATCH_NOTES.is_dir():
        return []
    notes = [path for path in PATCH_NOTES.glob('*.md') if path.stem[:4].isdigit()]
    return sorted(notes, key=note_key, reverse=True)

def markdown_document(path, level='header'):
    """Render a doc: its `# Title` as `st.<level>`, the rest as markdown."""
    try:
        title, body = read_document(path)
    except (OSError, UnicodeDecodeError) as problem:
        error(f'Could not read `{path}`: {problem}')
        return

    getattr(st, level)(title)
    st.markdown(body)

def expander_document(path):
    """Render a doc with its title as the expander label, so it appears once."""
    try:
        title, body = read_document(path)
    except (OSError, UnicodeDecodeError) as problem:
        error(f'Could not read `{path}`: {problem}')
        return

    with st.expander(title):
        st.markdown(body)
