from django.urls import path
from . import views # Import views from the current directory

urlpatterns = [
    path('', views.event_list, name='event_list'), # Root of the core app shows the list
    path('event/new/', views.event_create, name='event_create'),
    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    path('event/<int:pk>/score/<int:activity_id>/', views.score_activity, name='score_activity'),
]