import elasticsearch
from tastypie.resources import ModelResource
from django.conf.urls import url
from ..models import SavedSearch
from django.conf import settings
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.exceptions import Unauthorized

class MustBeScriptAuthorization(ReadOnlyAuthorization):
    def read_list(self, object_list, bundle):
        # This assumes a ``QuerySet`` from ``ModelResource``.
        if bundle.request.user.username in ["api_user", "g-clef"]:
            return object_list
        else:
            raise Unauthorized("must be api User")

    def read_detail(self, object_list, bundle):
        # Is the requested object owned by the user?
        if bundle.request.user.username in ["api_user", "g-clef"]:
            return True
        else:
            raise Unauthorized("must be api User")

class SavedSearchResource(ModelResource):
    class Meta:
        queryset = SavedSearch.objects.all()
        resource_name = "regexes"
        allowed_methods = ["get"]
        authentication = ApiKeyAuthentication()
        authorization = MustBeScriptAuthorization()

    def dehydrate(self, bundle):
        bundle.data['owner_email'] = bundle.obj.owner.email
        bundle.data['owner'] = bundle.obj.owner.username
        return bundle

class DummyPaginator(object):
    def __init__(self, request_data, objects, resource_uri=None,
                 limit=None, offset=0, max_limit=1000,
                 collection_name='objects'):
        self.objects = objects
        self.collection_name = collection_name

    def page(self):
        return { self.collection_name: self.objects, }


class Search(ModelResource):
    class Meta:
        resource_name = "search"
        allowed_methods = ['get', 'post']
        paginator_class = DummyPaginator
        authentication = ApiKeyAuthentication()

    def override_urls(self):
        return [ url(r'^search/query/$', self.wrap_view("get_pastes"), name="api_query"), ]

    def get_pastes(self, request, **kwargs):
        if request.method.lower() == "get":
            q = request.GET.get('q')
        else:
            q = request.POST.get("q")
        # do the query
        es = elasticsearch.Elasticsearch(settings.ElasticsearchURL)
        query = {"query": {"simple_query_string": { "query": q}},
                 "highlight": {"fields": {"*": {}}},
                 "size": "50"
                 }
        try:
            response = es.search(index=settings.ElasticsearchIndex, body=query)
        except elasticsearch.RequestError:
            response = [{"error":'error running query'},]
        except elasticsearch.ConnectionTimeout:
            response = [{"error": 'timeout running query'},]
        objects = []
        if "hits" in response and "hits" in response['hits']:
            for result in response['hits']['hits']:
                objects.append(result)
        return self.create_response(request, {"hits": objects})