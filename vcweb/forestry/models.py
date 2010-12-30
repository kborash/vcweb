from django.db import models
from vcweb.core import signals

from vcweb.core.models import ExperimentMetadata, Parameter


# Create your models here.
def forestry_second_tick(self):
    print "Monitoring Forestry Experiments."
    '''
    check all forestry experiments.
    '''


def get_resource_level(group=None):
    return group.get_group_data_values(name='resource_level') if group else []

def get_harvest_decisions(group=None):
    return group.get_participant_data_values(name='harvest_decision') if group else []

def get_harvest_decision_parameter():
# FIXME: crappy assumption that forestry is ExperimentMetadata 1
    experiment_metadata = ExperimentMetadata.objects.get(namespace='forestry')
    return Parameter.objects.get(
            name='harvest_decision',
            scope='PARTICIPANT_SCOPE',
            experiment_metadata=experiment_metadata)
