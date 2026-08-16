from django import template
from django.utils.safestring import mark_safe
import markdown

register = template.Library()


@register.filter(name='markdown')
def render_markdown(text):
    html_content = markdown.markdown(
        text,
        extensions=[
            'extra',
            'codehilite',
            'toc',
        ]
    )

    return mark_safe(html_content)