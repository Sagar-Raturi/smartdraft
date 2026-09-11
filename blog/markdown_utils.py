"""Shared Markdown -> safe HTML rendering.

Used by the `markdown` template filter (blog_tags.py) so published posts
render sanitized HTML, and by the `render_preview` view so the editor's
live preview matches the real rendering exactly (same extensions, same
sanitizer, same output).
"""
import bleach
import markdown

MARKDOWN_EXTENSIONS = ['extra', 'codehilite', 'toc']
MARKDOWN_EXTENSION_CONFIGS = {
    'codehilite': {'guess_lang': False},
}

# Tags/attributes Python-Markdown's 'extra' + 'codehilite' + 'toc' extensions
# can legitimately produce. Anything else (e.g. <script>, <iframe>, event
# handler attributes) is stripped so post content can never inject markup
# that the author didn't intend as formatting.
ALLOWED_TAGS = [
    'p', 'br', 'hr',
    'strong', 'b', 'em', 'i', 'u', 's', 'del',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li',
    'blockquote', 'pre', 'code', 'span', 'div',
    'a', 'img',
    'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
    'sup', 'sub', 'dl', 'dt', 'dd',
]

ALLOWED_ATTRIBUTES = {
    '*': ['id', 'class'],
    'a': ['href', 'title', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'th': ['align'],
    'td': ['align'],
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']


def render_markdown_safe(text):
    """Render Markdown source to sanitized HTML, safe to mark_safe()."""
    if not text:
        return ''

    html = markdown.markdown(
        text,
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )

    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
