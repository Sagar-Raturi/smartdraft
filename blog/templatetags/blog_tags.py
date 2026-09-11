from django import template
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe

from blog.markdown_utils import render_markdown_safe

register = template.Library()


@register.filter(name='markdown')
def render_markdown(text):
    return mark_safe(render_markdown_safe(text))


@register.filter(name='markdown_excerpt')
def markdown_excerpt(text, word_limit=40):
    """Plain-text preview of rendered Markdown, truncated to word_limit words.

    Renders through the same Markdown+sanitizer pipeline as the real post so
    things like **bold** or `code` don't leak into the excerpt as raw
    syntax, then strips tags entirely -- safe to drop straight into a <p>.
    """
    plain = strip_tags(render_markdown_safe(text))
    words = plain.split()
    if len(words) <= word_limit:
        return plain
    return ' '.join(words[:word_limit]) + '…'
