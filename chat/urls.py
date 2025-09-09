from django.urls import path
from . import views

urlpatterns = [
    path('', views.chatbot_view, name='chatbot'),
    path('runpod_proxy/', views.runpod_proxy, name='runpod-api'),
    path('cancel_runpod/', views.cancel_runpod_job, name='cancel_runpod_job'),
    # path('start-server/', views.start_runpod_server, name='start-server')
]