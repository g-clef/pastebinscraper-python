import elasticsearch
from django.conf import settings
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView
from django.views.generic.edit import FormView, CreateView, UpdateView, DeleteView
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from .models import ESSearchForm
from .models import SavedSearch

# Create your views here.

def require_customer_group(user):
    success = False
    if user:
        success = user.groups.filter(name="customer").count() == 1
        success |= user.is_staff
    if success:
        return True
    else:
        raise PermissionDenied


class IndexView(FormView):
    template_name = "ESsearch.html"
    form_class = ESSearchForm

    def form_valid(self, form):
        es = elasticsearch.Elasticsearch(settings.ElasticsearchURL, timeout=120)
        query = {"query": {"simple_query_string": { "query": form.cleaned_data['text']}},
                 "highlight": {"fields": {"*": {}}},
                 "size": "50"
                 }
        context = self.get_context_data()
        try:
            response = es.search(index=settings.ElasticsearchIndex, body=query)
            context['response'] = response['hits']['hits']
        except elasticsearch.RequestError:
            form.errors['__all__'] = form.error_class(['error running query'])
        except elasticsearch.ConnectionTimeout:
            form.errors['__all__'] = form.error_class(['timeout running query'])
        context['form'] = form
        return self.render_to_response(context)

    @method_decorator(login_required)
    @method_decorator(user_passes_test(require_customer_group))
    def dispatch(self, *args, **kwargs):
        return super(IndexView, self).dispatch(*args, **kwargs)


class ListSavedSearch(ListView):
    template_name = "savedSearchList.html"
    model = SavedSearch
    context_object_name = "searches"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        queryset = SavedSearch.objects.filter(owner=user)
        return queryset

    @method_decorator(login_required)
    @method_decorator(user_passes_test(require_customer_group))
    def dispatch(self, *args, **kwargs):
        return super(ListSavedSearch, self).dispatch(*args, **kwargs)


class ViewSavedSearch(DetailView):
    template_name = "searchDetail.html"
    model = SavedSearch
    contect_object_name = "search"

    def get(self, *args, **kwargs):
        instance = self.get_object()
        user = self.request.user
        if not user == instance.owner:
            raise PermissionDenied()
        return super(ViewSavedSearch, self).get(*args, **kwargs)

    @method_decorator(login_required)
    @method_decorator(user_passes_test(require_customer_group))
    def dispatch(self, *args, **kwargs):
        return super(ViewSavedSearch, self).dispatch(*args, **kwargs)


class UpdateSavedSearch(UpdateView):
    model = SavedSearch
    template_name = "searchupdate.html"
    success_url = reverse_lazy("paste:listsearches")

    def form_valid(self, form):
        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


    @method_decorator(login_required)
    @method_decorator(user_passes_test(require_customer_group))
    def dispatch(self, *args, **kwargs):
        user = self.request.user
        instance = self.get_object()
        if not user == instance.owner:
            raise PermissionDenied()
        return super(UpdateSavedSearch, self).dispatch(*args, **kwargs)


class NewSavedSearch(CreateView):
    template_name = "newSavedSearch.html"
    model = SavedSearch

    def form_valid(self, form):
        newObj = form.save(commit=False)
        newObj.owner = self.request.user
        newObj.save()
        return HttpResponseRedirect(reverse("paste:listsearches"))

    @method_decorator(login_required)
    @method_decorator(user_passes_test(require_customer_group))
    def dispatch(self, *args, **kwargs):
        return super(NewSavedSearch, self).dispatch(*args, **kwargs)

class DeleteSavedSearch(DeleteView):
    model = SavedSearch
    success_url = reverse_lazy("paste:listsearches")
    template_name = "confirmdelete.html"

    @method_decorator(login_required)
    @method_decorator(user_passes_test(require_customer_group))
    def dispatch(self, *args, **kwargs):
        user = self.request.user
        instance = self.get_object()
        if not user == instance.owner:
            raise PermissionDenied()
        return super(DeleteSavedSearch, self).dispatch(*args, **kwargs)

class EditMyself(UpdateView):
    model = User
    fields = ['email', 'first_name', 'last_name']
    template_name = "userupdate.html"

    def form_valid(self, form):
        form.save()
        context = self.get_context_data()
        context['edit_success'] = True
        context['form'] = form
        return self.render_to_response(context)

    @method_decorator(login_required)
    @method_decorator(user_passes_test(require_customer_group))
    def dispatch(self, *args, **kwargs):
        user = self.request.user
        instance = self.get_object()
        if not user.id == instance.id:
            raise PermissionDenied()
        return super(EditMyself, self).dispatch(*args, **kwargs)

class API(DetailView):
    model = User
    template_name = "api.html"

    @method_decorator(login_required)
    @method_decorator(user_passes_test(require_customer_group))
    def dispatch(self, *args, **kwargs):
        user = self.request.user
        instance = self.get_object()
        if not user.id == instance.id:
            raise PermissionDenied()
        return super(API, self).dispatch(*args, **kwargs)
