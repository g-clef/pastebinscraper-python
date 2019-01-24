from django.conf.urls import include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = [
                       url(r'^$', "ieatpaste.views.index", name="baseindex"),
                       url(r'^admin/', include(admin.site.urls)),
                       url(r'^accounts/', include('allauth.urls')),
                       url(r'^paste/', include('paste.urls', namespace="paste")),
                       ]