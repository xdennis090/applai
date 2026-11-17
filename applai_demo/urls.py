"""
URL configuration for applai_demo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib.auth import views as auth_views

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

from . import api_views
from core import views as core_views

schema_view = get_schema_view(
    openapi.Info(
        title="ApplAI API",
        default_version="v1",
        description="OpenAPI-Spezifikation fuer die JSON-API-Endpunkte.",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/login/', admin.site.login, name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', core_views.dashboard_view, name='home'),
    path('update_basisdaten/', core_views.update_basisdaten, name='update_basisdaten'),

    path('add_station/', core_views.add_station, name='add_station'),
    path('add-category-ajax/', core_views.add_category_ajax, name='add_category_ajax'),
    path('delete_category_ajax/', core_views.delete_category_ajax, name='delete_category_ajax'),
    path('station/delete/<int:pk>/', core_views.delete_station, name='delete_station'),
    path('station/get/<int:pk>/', core_views.get_station_data, name='get_station_data'),
    path('station/edit/<int:pk>/', core_views.edit_station, name='edit_station'),

    path('add_skill/', core_views.add_skill, name='add_skill'),
    path('delete_skill/<int:pk>/', core_views.delete_skill, name='delete_skill'),
    path('api/get_skills_options/', core_views.get_skills_options, name='get_skills_options'),

    path('delete_soft_skill/<int:pk>/', core_views.delete_soft_skill, name='delete_soft_skill'),

    path('add_leistung/<int:station_id>/', core_views.add_leistung, name='add_leistung'),
    path('delete_leistung/<int:pk>/', core_views.delete_leistung, name='delete_leistung'),

    path('add_project_skill/<int:leistung_id>/', core_views.add_project_skill, name='add_project_skill'),
    path('delete_project_skill/<int:pk>/', core_views.delete_project_skill, name='delete_project_skill'),

    path('export-pdf/', core_views.export_pdf_view, name='export_pdf'),

    path('api/session/', api_views.session_view, name='api-session'),
    path('api/login/', api_views.login_view, name='api-login'),
    path('api/logout/', api_views.logout_view, name='api-logout'),
    path('api/register/', api_views.register_view, name='api-register'),
    path('api/profile/', api_views.profile_view, name='api-profile'),
    path('api/jobs/search/', api_views.jobs_search_view, name='api-jobs-search'),
    path('api/jobs/bookmarks/', api_views.jobs_bookmarks_view, name='api-jobs-bookmarks'),
    path('api/jobs/bookmarks/delete/', api_views.jobs_bookmarks_delete_view, name='api-jobs-bookmarks-delete'),
    path('api/assistant/generate/', api_views.assistant_generate_view, name='api-assistant-generate'),
    path('api/assistant/history/', api_views.assistant_history_view, name='api-assistant-history'),
    path('api/assistant/chat/', api_views.assistant_chat_view, name='api-assistant-chat'),
    path('api/assistant/save/', api_views.assistant_save_view, name='api-assistant-save'),
    path('api/assistant/delete/', api_views.assistant_delete_view, name='api-assistant-delete'),
    path('api/openapi.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/ollama/models/', api_views.ollama_models_view, name='api-ollama-models'),
    path('api/comfy/models/', api_views.comfy_models_view, name='api-comfy-models'),
    path('api/photos/generate/', api_views.photos_generate_view, name='api-photos-generate'),
    path('api/photos/optimize/', api_views.photos_optimize_view, name='api-photos-optimize'),
    path('api/photos/history/', api_views.photos_history_view, name='api-photos-history'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
