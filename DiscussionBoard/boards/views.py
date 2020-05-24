from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import UpdateView, ListView
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.urls import reverse

from .forms import NewTopicForm, PostForm
from .models import Board, Post, Topic
import requests

class BoardListView(ListView):   # <-- get a collection of values from the database (Board table)
    model = Board
    context_object_name = 'boards'
    template_name = 'home.html'

    # for filtering
    # def get_queryset() # <--- use for filtering the results (filter the boards)
    def get_queryset(self):
        query_set = super().get_queryset()
        return query_set.filter(name__startswith='')

    def get_context_data(self, **kwargs):  # <--- return a dictionary instead of just the query set
        data = super(BoardListView, self).get_context_data(**kwargs)
        data['search_expression'] = self.search_expression 
        data['chardata'] = self.chardata
        return data

    # def get(self, request)  # <-- use this to  handle a get request from start to finish
    def get(self, request, *args, **kwargs):
        self.search_expression = request.GET.get('character')
        if self.search_expression != None:
            #url = 'https://randomuser.me/api/'
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
            url = 'https://comicvine.gamespot.com/api/characters/?api_key=340afe8dcda8eeec5bf1675ae3cdb06a6f565334&format=json&filter=name:deadpool'
            response = requests.get(url, headers=headers)
            print(response)
            self.chardata = response.json()
            print(self.chardata)
           # self.chardata = { 'first_appeared_in_issue': '1' }
        else:
            print('NO API REQUEST')
            self.chardata = { 'first_appeared_in_issue': '2' }
        return super(BoardListView, self).get(request, *args, **kwargs)




    # def post(self, request):
        # post_value =  request.POST.get("search")
        # boards = super().get_queryset()
        # Not necessarily good structure, but API requests can be fired here
        #response = response.get('https://api.shortboxed.com/comics/v1/new')
        # return render(request, self.template_name, {'boards': boards, 'post_value': post_value})


class TopicListView(ListView):
    model = Topic
    context_object_name = 'topics'
    template_name = 'topics.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        kwargs['board'] = self.board
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        self.board = get_object_or_404(Board, pk=self.kwargs.get('pk'))
        queryset = self.board.topics.order_by('-last_updated').annotate(replies=Count('posts') - 1)
        return queryset


class PostListView(ListView):
    model = Post
    context_object_name = 'posts'
    template_name = 'topic_posts.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        session_key = 'viewed_topic_{}'.format(self.topic.pk)
        if not self.request.session.get(session_key, False):
            self.topic.views += 1
            self.topic.save()
            self.request.session[session_key] = True
        kwargs['topic'] = self.topic
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        self.topic = get_object_or_404(Topic, board__pk=self.kwargs.get('pk'), pk=self.kwargs.get('topic_pk'))
        queryset = self.topic.posts.order_by('created_at')
        return queryset


@login_required
def new_topic(request, pk):
    board = get_object_or_404(Board, pk=pk)
    if request.method == 'POST':
        form = NewTopicForm(request.POST)
        if form.is_valid():
            topic = form.save(commit=False)
            topic.board = board
            topic.starter = request.user
            topic.save()
            Post.objects.create(
                message=form.cleaned_data.get('message'),
                topic=topic,
                created_by=request.user
            )
            return redirect('topic_posts', pk=pk, topic_pk=topic.pk)
    else:
        form = NewTopicForm()
    return render(request, 'new_topic.html', {'board': board, 'form': form})


@login_required
def reply_topic(request, pk, topic_pk):
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk)
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.topic = topic
            post.created_by = request.user
            post.save()

            topic.last_updated = timezone.now()
            topic.save()

            topic_url = reverse('topic_posts', kwargs={'pk': pk, 'topic_pk': topic_pk})
            topic_post_url = '{url}?page={page}#{id}'.format(
                url=topic_url,
                id=post.pk,
                page=topic.get_page_count()
            )

            return redirect(topic_post_url)
    else:
        form = PostForm()
    return render(request, 'reply_topic.html', {'topic': topic, 'form': form})


@method_decorator(login_required, name='dispatch')
class PostUpdateView(UpdateView):
    model = Post
    fields = ('message', )
    template_name = 'edit_post.html'
    pk_url_kwarg = 'post_pk'
    context_object_name = 'post'

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(created_by=self.request.user)

    def form_valid(self, form):
        post = form.save(commit=False)
        post.updated_by = self.request.user
        post.updated_at = timezone.now()
        post.save()
        return redirect('topic_posts', pk=post.topic.board.pk, topic_pk=post.topic.pk)