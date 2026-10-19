from django import template

from eventyay.common.views.redirect import safelink as sl
from eventyay.helpers.safedownload import get_token

register = template.Library()


@register.simple_tag
def safelink(url):
    return sl(url)


@register.simple_tag
def answer_token(request, answer):
    return get_token(request, answer)
