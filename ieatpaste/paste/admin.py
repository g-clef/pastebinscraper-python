from django.contrib import admin
from .models import SavedSearch
from django.contrib.auth.models import User
from django.db import models
from tastypie.models import create_api_key

# Register your models here.

admin.site.register(SavedSearch)

# auto-create api key when user is created.
models.signals.post_save.connect(create_api_key, sender=User)