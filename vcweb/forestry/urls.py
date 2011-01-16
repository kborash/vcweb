from django.conf.urls.defaults import url, patterns
'''
Created on Jul 14, 2010

@author: alllee
'''
urlpatterns = patterns('vcweb.forestry.views',
    url(r'^$', 'index', name='index'),
    url(r'configure/(?P<experiment_id>\d+)$', 'configure', name='configure'),
    url(r'(?P<experiment_id>\d+)/experimenter$', 'experimenter', name='experimenter'),
    url(r'(?P<experiment_id>\d+)', 'participate', name='participate'),
)
