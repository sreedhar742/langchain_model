from django.urls import path
from .views import FileUploadAPIView, QueryAPIView, FileListAPIView,getRoutes
urlpatterns = [
    path('',getRoutes,name="home"),
    path("upload/", FileUploadAPIView.as_view(), name="file-upload"),
    path("query/<int:file_id>/", QueryAPIView.as_view(), name="query"),
    path("files/", FileListAPIView.as_view(), name="file-list"),
]
