from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Post
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required

import os 
from django.conf import settings
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage

# # def home(request): 
# # 	context = {'posts': Post.objects.all()}
# # 	return render(request, 'blog/home.html', context)

# 	def form_valid(self, form):
# 		form.instance.autuor = self.request.user
# 		return super().form_valid(form)

def about(request):
	return HttpResponse('This is about page')


class PostListView(ListView):
	model = Post
	template_name = 'blog/home.html'
	context_object_name = 'posts'
	ordering = ['-date_posted']
	paginate_by = 5

class UserPostListView(ListView):
	model = Post 
	template_name = 'blog/user_posts.html'
	context_object_name = 'posts'
	paginate_by = 5

	def get_queryset(self):
		user = get_object_or_404(User, username=self.kwargs.get('username'))
		return Post.objects.filter(author=user).order_by('-date_posted')

class PostDetailView(DetailView):
	model = Post

class PostCreateView(LoginRequiredMixin, CreateView):
	model = Post
	fields = ['title', 'content']

	def form_valid(self, form):
		form.instance.author = self.request.user 
		return super().form_valid(form)

class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
	model = Post 
	fields = ['title', 'content']

	def form_valid(self, form):
		form.instance.author = self.request.user 
		return super().form_valid(form)

	def test_func(self):
		post = self.get_object()
		if self.request.user == post.author:
			return True 
		return False

class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
	model = Post 
	success_url = '/'

	def test_func(self):
		post = self.get_object()
		if self.request.user == post.author:
			return True
		return False 

@login_required
def upvote_post(request, slug):
	post = get_object_or_404(Post, slug=slug)

	if post.upvotes.filter(id=request.user.id).exists():
		post.upvotes.remove(request.user)
	else:
		post.upvotes.add(request.user)

	return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def upload_image(request):
    # EasyMDE sends the uploaded file in request.FILES['image']
    if request.method == 'POST' and request.FILES.get('image'):
        image = request.FILES['image']
        
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
        fs = FileSystemStorage(location=upload_dir, base_url=f"{settings.MEDIA_URL}uploads/")
        filename = fs.save(image.name, image)
        uploaded_file_url = fs.url(filename)

        # EasyMDE requires this exact JSON response
        return JsonResponse({
            "data": {
                "filePath": uploaded_file_url
            }
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)




