from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<graph>missing_children).*$', views.getGraph, name='missing_children'),
    url(r'^(?P<graph>Datapower 500s).*$', views.getGraph, name='myMSD_log_errors'),
    url(r'^(?P<graph>Outgoing Letter Size).*$', views.getGraph, name='mymsdpweb_letter_size'),
    url(r'^(?P<graph>mymsd_log_errors).*$', views.getGraph, name='mymsd_log_errors'),
    url(r'^(?P<graph>Concurrent Connections).*$', views.getGraphGroupBy, name='concurrent_connections'),
    url(r'^(?P<graph>test1).*$', views.getGraph, name='test1'),
    url(r'^(?P<graph>test2).*$', views.getGraph, name='test2'),
    url(r'^(?P<graph>Service Performance).*$', views.getGraphGroupBy, name='all_graphs'),

]