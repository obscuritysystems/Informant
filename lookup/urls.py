import os.path
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings
from lookup import views
site_media = os.path.join(os.path.dirname(__file__), 'site_media')

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^member/$', views.member,name='member'),
    url(r'^create_group/$', views.create_group,name='create_group'),
    url(r'^show_group/(?P<group_id>\d+)$', views.show_group,name='show_group'),
    url(r'^run_search/', views.run_search,name='run_search'),
    url(r'^show_search/(?P<search_id>\d+)$', views.show_search,name='show_search'),
    url(r'^login/$', views.login,name='login'),
    url(r'^logout/$', views.logout_page, name='logout'),
)

