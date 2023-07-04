from django.shortcuts import render, reverse, get_object_or_404
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .models import User, Room, Message


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("lobby"))
        else:
            return "Incorrect username or password. PLease log in."
    return render(request, 'registration/login.html')


@login_required
def lobby(request):
    if request.method == "POST":
        name = request.POST.get("name", None)
        if name:
            room = Room.objects.create(name=name, host=request.user)
            HttpResponseRedirect(reverse("room", args=[room.pk]))
    return render(request, 'chat/lobby.html')


@login_required
def room(request, pk):
    room: Room = get_object_or_404(Room, pk=pk)
    return render(request, 'chat/room.html', {
        "room": room,
    })

