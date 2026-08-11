from django.contrib import admin
from django.urls import path, include
from .views import PostListView, UserPostListView, PostDetailView, PostCreateView, PostUpdateView, PostDeleteView, upvote_post
from . import views

urlpatterns = [
    path('', PostListView.as_view(), name='home'),
    path('post/new/', PostCreateView.as_view(), name='post-create'),
    path('user/<str:username>/', UserPostListView.as_view(), name='user-posts'),
    path('post/<slug:slug>/', PostDetailView.as_view(), name='post-detail'),
    path('post/<slug:slug>/update/', PostUpdateView.as_view(), name='post-update'),
    path('post/<slug:slug>/delete/', PostDeleteView.as_view(), name='post-delete'),

    path('about/', views.about, name = "about"),

    path('post/<slug:slug>/upvote/', views.upvote_post, name='upvote-post'),

]