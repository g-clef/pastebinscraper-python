from django import template
import datetime

register = template.Library()

@register.filter(name="get")
def get(d,k):
    return d.get(k, None)

@register.filter(name="getattrib")
def getattrib(obj, attrib):
    if hasattr(obj, attrib):
        return getattr(obj, attrib)
    else:
        return None

@register.filter(name="fromtimestamp")
def fromtimestamp(target):
    target = float(target)
    if target == 0.0:
        return ""
    else:
        return datetime.datetime.fromtimestamp(target).strftime("%Y-%m-%d %H:%M:%S")
