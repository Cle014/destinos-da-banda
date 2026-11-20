from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import RedirectView
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static

handler404 = 'apps.core.views.handler_404'
handler500 = 'apps.core.views.handler_500'

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('', include('apps.core.urls')),

    path('destinos/', include('apps.destinations.urls')),
    path('galeria/', include('apps.gallery.urls')),
    path('alojamentos/', include('apps.accommodations.urls')),
    path('eventos/', include('apps.events.urls')),
    path('rotas/', include('apps.routes.urls')),
    path('guias/', include('apps.guides.urls')),
    path(settings.DASHBOARD_URL, include('apps.dashboard.urls')),
]

if settings.ADMIN_URL != 'admin/':
    urlpatterns.insert(0, path('admin/', RedirectView.as_view(pattern_name='dashboard:home', permanent=False)))

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    try:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass
else:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
