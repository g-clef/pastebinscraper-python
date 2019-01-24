from django.conf.urls import include, url
from tastypie.api import Api
#from paste.api.resources import UserResource
from .api.resources import SavedSearchResource
from .api.resources import Search
from . import views

v1_api = Api(api_name="v1")
#v1_api.register(UserResource())
v1_api.register(SavedSearchResource())
v1_api.register(Search())

urlpatterns = [
               url(r'^$', views.IndexView.as_view(), name="index"),
               url(r'^searches/$', views.ListSavedSearch.as_view(), name="listsearches"),
               url(r'^searches/(?P<pk>\d+)/edit', views.UpdateSavedSearch.as_view(), name="searchedit"),
               url(r'^searches/(?P<pk>\d+)/delete', views.DeleteSavedSearch.as_view(), name="searchdelete"),
               url(r'^searches/new$', views.NewSavedSearch.as_view(), name="newsearch"),
               url(r'^aboutapi/(?P<pk>\d+)/$', views.API.as_view(), name="aboutapi"),
               url(r'^contact/(?P<pk>\d+)/$', views.EditMyself.as_view(), name="editmyself"),
               url(r'^api/', include(v1_api.urls))
               ]