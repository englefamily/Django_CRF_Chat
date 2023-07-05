from django.shortcuts import redirect, render, reverse, get_object_or_404
from django.http import HttpResponseRedirect
from .models import User, Room, Message
from django.contrib.auth import authenticate, login, get_user_model

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('lobby')
        else:
            # TODO: Add error handling for invalid credentials
            pass
    return render(request, 'chat/lobby.html')

def lobby(request):
    if request.method == "POST":
        name = request.POST.get("name", None)
        if name:
            room = Room.objects.create(name=name, host=request.user)
            return HttpResponseRedirect(reverse("room", args=[room.pk]))
    return render(request, 'chat/lobby.html')

def room(request, pk=None):
    if pk is not None:
        room = get_object_or_404(Room, pk=pk)
        return render(request, 'chat/room.html', {
            "room": room,
        })
    else:
        if request.method == 'POST':
            room_name = request.POST.get('name')
            if room_name:
                room = Room.objects.create(name=room_name, host=request.user if request.user.is_authenticated else None)
                return HttpResponseRedirect(reverse('room', args=[room.pk]))
        return redirect('lobby')
