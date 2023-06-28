from django.urls import path
from . import views

urlpatterns = [
    path('', views.lobby, name="lobby"),
    path('room/<int:pk>/', views.room, name='room'),
    ]
