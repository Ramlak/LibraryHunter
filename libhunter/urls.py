__author__ = 'kalmar'

from django.conf.urls import patterns, url
from libhunter import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^add/$', views.add, name='add'),
    url(r'^result/$', views.result, name='result'),
    url(r'^list/$', views.list, name='list'),
    url(r'^libs/add/$', views.add_lib, name='add_lib'),
    url(r'^libs/show/(?P<id>\d+)/$', views.show, name='show'),
    url(r'^libs/all/$', views.download_all, name='download_all'),
    url(r'^libs/(?P<id>\d+)/$', views.download, name='download'),
    url(r'^info/$', views.info, name='info'),
    )
