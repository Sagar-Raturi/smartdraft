from django.shortcuts import render

from django.shortcuts import render, redirect
from .forms import ProfileUpdateForm, UserUpdateForm

def profile(request):

	if request.method == 'POST':
		p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
		u_form = UserUpdateForm(request.POST, instance = request.user.profile)

		if u_form.is_valid() and p_form.is_valid():
			u_form.save()
			p_form.save()
			return redirect('profile')

	else:
		p_form = ProfileUpdateForm(instance = request.user.profile)
		u_form = UserUpdateForm(instance = request.user.profile)

	context = { 'u_form': u_form, 'p_form': p_form }

	return render(request, 'users/profile.html', { 'context' : context })
