from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('event/new/', views.event_create, name='event_create'),
    path('event/<int:pk>/', views.event_detail, name='event_detail'),
    
    # Scoring URLs
    path('event/<int:pk>/score/<int:activity_id>/', views.score_activity, name='score_activity'),
    path('event/<int:pk>/tennis/', views.tennis_tournament, name='tennis_tournament'),
    path('event/<int:pk>/running/', views.running_page, name='running_page'),

    # API URLs
    path('event/<int:pk>/api/record_match/', views.record_tennis_match, name='record_tennis_match'),
    path('event/<int:pk>/api/record_running/', views.record_running_time, name='record_running_time'),
    # Support the frontend JS path which posts to /event/<pk>/running/api/record_running/
    path('event/<int:pk>/running/api/record_running/', views.record_running_time, name='record_running_time_running_path'),
    path('event/<int:pk>/api/delete_running/', views.delete_running_time, name='delete_running_time'),
    path('event/<int:pk>/running/api/delete_running/', views.delete_running_time, name='delete_running_time_running_path'),
    path('portal/', views.portal, name='portal'),
]