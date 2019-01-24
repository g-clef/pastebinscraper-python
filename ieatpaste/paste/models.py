from django.db import models
from django.contrib.auth.models import User
from django import forms
# Create your models here.


class SavedSearch(models.Model):
    owner = models.ForeignKey(User)
    body = models.TextField(blank=True)
    author = models.TextField(blank=True)


class ESSearchForm(forms.Form):
    text = forms.CharField(widget=forms.TextInput(attrs={"placeholder": "query",
                                                         "class": "col-md-10"}))


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', "first_name", "last_name"]