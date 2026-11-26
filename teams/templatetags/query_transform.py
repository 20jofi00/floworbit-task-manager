from django import template
from django.http import HttpRequest

register = template.Library()


@register.simple_tag
def query_transform(request: HttpRequest, **kwargs):
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value is not None:
            updated[key] = value
        else:
            updated.pop(key, 0)
    return updated.urlencode()

@register.simple_tag
def pagination_query(request, page_number, page_parameter="page"):
    return query_transform(request, **{page_parameter: page_number})

