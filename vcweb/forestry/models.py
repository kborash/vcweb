from django.dispatch import receiver
from vcweb.core.models import (ExperimentMetadata, Parameter, ParticipantRoundDataValue)
from vcweb.core import signals, simplecache
import logging
logger = logging.getLogger(__name__)

EXPERIMENT_METADATA_NAME = intern('forestry')
MAX_RESOURCE_LEVEL = 100

def get_resource_level_dv(group, round_data=None, default=MAX_RESOURCE_LEVEL):
    return group.get_data_value(parameter=get_resource_level_parameter(), round_data=round_data, default=default)

def get_resource_level(group, round_data=None, **kwargs):
    ''' returns the group resource level data value scalar '''
    return get_resource_level_dv(group, round_data=round_data, **kwargs).int_value

def get_group_harvest_dv(group, round_data=None):
    ''' returns the collective group harvest data value '''
    return group.get_data_value(parameter=get_group_harvest_parameter(), round_data=round_data)

def get_group_harvest(group, round_data=None):
    ''' returns the collective group harvest data value '''
    return group.get_data_value(parameter=get_group_harvest_parameter(), round_data=round_data).int_value

def get_regrowth_dv(group, round_data=None):
    return group.get_data_value(parameter=get_regrowth_parameter(), round_data=round_data, default=0)
# returns the number of resources regenerated for the given group in the given round
def get_regrowth(group, round_data=None):
    return group.get_data_value(parameter=get_regrowth_parameter(), round_data=round_data, default=0).int_value

def get_regrowth_rate(current_round, default=0.1):
    return current_round.get_parameter_value(get_regrowth_rate_parameter(), default=default).float_value

def has_resource_level(group=None):
    return group.has_data_parameter(parameter=get_resource_level_parameter())

def get_harvest_decision_dv(participant_group_relationship, round_data=None, default=0):
    return participant_group_relationship.get_data_value(round_data=round_data, parameter=get_harvest_decision_parameter(), default=default)

def get_harvest_decision(participant_group_relationship, round_data=None, default=0):
    return get_harvest_decision_dv(participant_group_relationship, round_data, default).int_value

def get_harvest_decisions(group=None):
    return group.get_participant_data_values(parameter__name='harvest_decision') if group else []

def set_regrowth(group, value, round_data=None):
    group.set_data_value(parameter=get_regrowth_parameter(), value=value, round_data=round_data)

def set_group_harvest(group, value, round_data=None):
    group.set_data_value(parameter=get_group_harvest_parameter(), value=value, round_data=round_data)

def should_reset_resource_level(round_configuration):
    return round_configuration.get_parameter_value(parameter=get_reset_resource_level_parameter(), default=False).boolean_value

def get_initial_resource_level(round_configuration, default=MAX_RESOURCE_LEVEL):
    return round_configuration.get_parameter_value(parameter=get_initial_resource_level_parameter(), default=default).int_value

def get_max_harvest_decision(resource_level):
    if resource_level >= 25:
        return 5
    elif resource_level >= 20:
        return 4
    elif resource_level >= 15:
        return 3
    elif resource_level >= 10:
        return 2
    elif resource_level >= 5:
        return 1
    else:
        return 0

@simplecache
def get_forestry_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='forestry')

@simplecache
def get_resource_level_parameter():
    return Parameter.objects.for_group(name='resource_level')

@simplecache
def get_regrowth_rate_parameter():
    return Parameter.objects.for_round(name='regrowth_rate')

# parameter for the amount of resources that were regrown at the end of the given round for the given group
@simplecache
def get_regrowth_parameter():
    return Parameter.objects.for_group(name='group_regrowth')

@simplecache
def get_group_harvest_parameter():
    return Parameter.objects.for_group(name='group_harvest')

@simplecache
def get_harvest_decision_parameter():
    return Parameter.objects.for_participant(name='harvest_decision')

@simplecache
def get_reset_resource_level_parameter():
    return Parameter.objects.for_round(name='reset_resource_level')

@simplecache
def get_initial_resource_level_parameter():
    return Parameter.objects.for_round(name='initial_resource_level')

def set_harvest_decision(participant_group_relationship=None, value=None, round_data=None, submitted=False):
    if round_data is None:
        round_data = participant_group_relationship.current_round_data
# deactivate all previous harvest decisions in this round
    ParticipantRoundDataValue.objects.for_participant(participant_group_relationship,
            parameter=get_harvest_decision_parameter(),
            round_data=round_data).update(is_active=False)
    return ParticipantRoundDataValue.objects.create(participant_group_relationship=participant_group_relationship,
            parameter=get_harvest_decision_parameter(), round_data=round_data,
            int_value=value,
            submitted=submitted)

def set_resource_level(group, value, round_data=None):
    return group.set_data_value(parameter=get_resource_level_parameter(), round_data=round_data, value=value)

@receiver(signals.round_started, sender=EXPERIMENT_METADATA_NAME)
def round_setup(sender, experiment=None, **kwargs):
    round_configuration = experiment.current_round
    logger.debug("setting up forestry round %s", round_configuration)
    if round_configuration.is_playable_round:
        # FIXME: push this step into the realm of experiment configuration
        # initialize group and participant data values
        experiment.initialize_data_values(
                group_parameters=(get_regrowth_parameter(), get_group_harvest_parameter(), get_resource_level_parameter()),
                participant_parameters=[get_harvest_decision_parameter()]
                )
        '''
        during a practice or regular round, set up resource levels and participant
        harvest decision parameters
        '''
        if should_reset_resource_level(round_configuration):
            initial_resource_level = get_initial_resource_level(round_configuration)
            logger.debug("Resetting resource level for %s to %d", round_configuration, initial_resource_level)
            round_data = experiment.get_round_data(round_configuration)
            for group in experiment.group_set.all():
                ''' set resource level to initial default '''
                group.log("Setting resource level to initial value [%s]" % initial_resource_level)
                set_resource_level(group, initial_resource_level, round_data=round_data)

@receiver(signals.round_ended, sender=EXPERIMENT_METADATA_NAME)
def round_ended(sender, experiment=None, **kwargs):
    logger.debug("forestry handling round ended signal")
    '''
    calculates new resource levels for practice or regular rounds based on the group harvest and resultant regrowth.
    also responsible for transferring those parameters to the next round as needed.
    '''
    round_data = experiment.current_round_data
    current_round_configuration = round_data.round_configuration
    logger.debug("current round: %s", current_round_configuration)
    max_resource_level = MAX_RESOURCE_LEVEL
    for group in experiment.groups:
        # FIXME: simplify logic
        logger.debug("group %s has resource level", group)
        if has_resource_level(group):
            current_resource_level_dv = get_resource_level_dv(group, round_data)
            current_resource_level = current_resource_level_dv.int_value
            group_harvest_dv = get_group_harvest_dv(group, round_data)
            regrowth_dv = get_regrowth_dv(group, round_data)
            if current_round_configuration.is_playable_round:
                # FIXME: update this to use django queryset aggregation ala boundaries experiment
                total_harvest = sum( [ hd.value for hd in get_harvest_decisions(group).all() ])
                logger.debug("total harvest for playable round: %d", total_harvest)
                if current_resource_level > 0 and total_harvest > 0:
                    group.log("Harvest: removing %s from current resource level %s" % (total_harvest, current_resource_level))
                    group_harvest_dv.update_int(total_harvest)
                    current_resource_level = max(current_resource_level - total_harvest, 0)
                    # implements regrowth function inline
                    # FIXME: parameterize regrowth rate.
                    regrowth = current_resource_level / 10
                    group.log("Regrowth: adding %s to current resource level %s" % (regrowth, current_resource_level))
                    regrowth_dv.update_int(regrowth)
                    current_resource_level_dv.update_int(min(current_resource_level + regrowth, max_resource_level))
            ''' transfer resource levels across chat and quiz rounds if they exist '''
            if experiment.has_next_round:
                ''' set group round data resource_level for each group + regrowth '''
                group.log("Transferring resource level %s to next round" % current_resource_level_dv.int_value)
# FIXME: technically group harvest and regrowth data values should be re-initialized each round.  Maybe push initialize
# data values flag into round parameter values
                group.copy_to_next_round(current_resource_level_dv, group_harvest_dv, regrowth_dv)
