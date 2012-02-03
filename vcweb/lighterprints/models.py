from django.db import models
from django.db.models import Q
from vcweb.core import signals, simplecache
from vcweb.core.models import (Experiment, ExperimentMetadata, Experimenter,
        GroupRoundDataValue, ParticipantRoundDataValue, Parameter)
from django.dispatch import receiver
from decimal import Decimal
import collections
import datetime
import logging
logger = logging.getLogger(__name__)

class Activity(models.Model):
    name = models.CharField(max_length=32, unique=True)
    display_name = models.CharField(max_length=64, null=True, blank=True)
    summary = models.CharField(max_length=256)
    description = models.TextField()
    url = models.URLField()
    savings = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    available_all_day = models.BooleanField(default=False)
    personal_benefits = models.TextField(null=True, blank=True)
# FIXME: allow for experiment-configurable levels?
    level = models.PositiveIntegerField(default=1)
    group_activity = models.BooleanField(default=False, help_text='Whether or not this activity has beneficial group effect multipliers, e.g., ride sharing')
    cooldown = models.PositiveIntegerField(default=1, null=True, blank=True, help_text='How much time, in hours, must elapse before this activity can become available again')
    icon = models.ImageField(upload_to='lighterprints/activity-icons/')

    @property
    def label(self):
        return self.display_name if self.display_name else self.name

    @property
    def icon_name(self):
        return self.name

    @property
    def icon_url(self):
        return self.icon.url if self.icon else ""

    def to_dict(self, attrs=('pk', 'name', 'summary', 'display_name', 'description', 'savings', 'url', 'available_all_day', 'level', 'group_activity', 'icon_url', 'time_remaining')):
        activity_as_dict = {}
        for attr_name in attrs:
            activity_as_dict[attr_name] = getattr(self, attr_name, None)
        return activity_as_dict

    def __unicode__(self):
        return u'%s (+%s)' % (self.label, self.savings)

    class Meta:
        ordering = ['level', 'name']

class ActivityAvailability(models.Model):
    activity = models.ForeignKey(Activity, related_name='availability_set')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def __unicode__(self):
        return u'%s (%s - %s)' % (self.activity, self.start_time, self.end_time)

    @property
    def time_slot(self):
        return u'%s - %s' % (self.start_time.strftime('%I:%M %p'), self.end_time.strftime('%I:%M %p'))

    def to_dict(self, attrs=('start_time', 'end_time')):
        d = {}
        for attr_name in attrs:
            d[attr_name] = getattr(self, attr_name, None)
        return d

    class Meta:
        ordering = ['activity', 'start_time']

@simplecache
def get_lighterprints_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='lighterprints')

def create_activity_performed_parameter(experimenter=None):
    if experimenter is None:
        experimenter = Experimenter.objects.get(pk=1)
    parameter, created = Parameter.objects.get_or_create(name='activity_performed', scope=Parameter.PARTICIPANT_SCOPE, type='int',
            creator=experimenter, experiment_metadata=get_lighterprints_experiment_metadata())
    if created: logger.debug("created activity performed parameter %s", parameter)
    return parameter

@simplecache
def get_activity_performed_parameter():
    return Parameter.objects.get(name='activity_performed')

@simplecache
def get_carbon_footprint_level_parameter():
    return Parameter.objects.get(name='carbon_footprint_level')

def get_carbon_footprint_level(group):
    return GroupRoundDataValue.objects.get(group=group, parameter=get_carbon_footprint_level_parameter())

def get_active_experiments():
    return Experiment.objects.filter(experiment_metadata=get_lighterprints_experiment_metadata(),
            status__in=('ACTIVE', 'ROUND_IN_PROGRESS'))

# FIXME: push into Activity class itself
def to_activity_dict(activity, attrs=('pk', 'name', 'summary', 'display_name', 'description', 'savings', 'url', 'available_all_day', 'level', 'group_activity', 'icon_url', 'time_remaining')):
    activity_as_dict = {}
    for attr_name in attrs:
        activity_as_dict[attr_name] = getattr(activity, attr_name, None)
    return activity_as_dict

# returns a tuple of (flattened_activities list + activity_by_level dict)
def get_all_available_activities(participant_group_relationship, all_activities=None):
    if all_activities is None:
        all_activities = Activity.objects.all()
    flattened_activities = []
    activity_by_level = collections.defaultdict(list)

    for activity in all_activities:
        activity_by_level[activity.level].append(activity)
        #activity_as_dict = collections.OrderedDict()
        activity_as_dict = to_activity_dict(activity)
        try:
            activity_as_dict['availabilities'] = [availability.to_dict() for availability in ActivityAvailability.objects.filter(activity=activity)]
            activity_as_dict['available'] = is_activity_available(activity, participant_group_relationship)
            activity_as_dict['time_slots'] = ','.join([av.time_slot for av in activity.availability_set.all()])
        except Exception as e:
            logger.debug("failed to get authenticated activity list: %s", e)
        flattened_activities.append(activity_as_dict)
    return (flattened_activities, activity_by_level)

def available_activities(activity=None):
    current_time = datetime.datetime.now().time()
    available_time_slot = dict(start_time__lte=current_time, end_time__gte=current_time)
    if activity is not None:
        available_time_slot['activity'] = activity
    activities = [activity_availability.activity for activity_availability in ActivityAvailability.objects.select_related(depth=1).filter(Q(**available_time_slot))]
    logger.debug("activities: %s", activities)
    activities.extend(Activity.objects.filter(available_all_day=True))
    return activities

def is_activity_available(activity, participant_group_relationship, **kwargs):
    # FIXME: make sure that the activity level is appropriate for this PGR
# how often can a participant participate in an activity?
# whenever it falls within the ActivityAvailability schedule and if the participant
# hasn't already performed this activity during this cycle.
    logger.debug("checking if %s is available for %s", activity, participant_group_relationship)
    level = get_carbon_footprint_level(participant_group_relationship.group)
    if activity.level > level:
        logger.debug("activity %s had larger level (%s) than group level (%s)", activity, activity.level, level)
        return False
    elif activity.available_all_day:
        # check if they've done it already today, check if the combine is necessary
        today = datetime.datetime.combine(datetime.date.today(), datetime.time())
        already_performed = ParticipantRoundDataValue.objects.filter(parameter=get_activity_performed_parameter(),
                participant_group_relationship=participant_group_relationship,
                int_value=activity.id,
                date_created__gt=today)
        logger.debug("activity is available all day, was it already performed? %s", already_performed)
        return already_performed.count() == 0
    else:
        logger.debug("XXX: wasn't available all day")
        now = datetime.datetime.now()
        current_time = now.time()
        # FIXME: check if this participant has already participated in this activity within this particular interval (for all
        # day, today, for time slots, during this particular time slot). There should only be one availability
        try:
            logger.debug("checking availability set %s", activity.availability_set.all())
            availabilities = activity.availability_set.filter(start_time__lte=current_time, end_time__gte=current_time)
            earliest_start_time = datetime.datetime.combine(datetime.date.today(), availabilities[0].start_time)
            logger.debug("earliest start time: %s", earliest_start_time)
            already_performed = ParticipantRoundDataValue.objects.filter(parameter=get_activity_performed_parameter(),
                    participant_group_relationship=participant_group_relationship,
                    int_value=activity.pk,
                    date_created__lte=now,
                    date_created__gte=earliest_start_time)
            return already_performed.count() == 0
        except:
            logger.debug("exception while checking if this activity had already been performed by this participant")
            return False

def do_activity(activity, participant_group_relationship):
    if is_activity_available(activity, participant_group_relationship):
        logger.debug("activity %s was available", activity)
        round_data = participant_group_relationship.group.current_round_data
        return ParticipantRoundDataValue.objects.create(parameter=get_activity_performed_parameter(),
                participant_group_relationship=participant_group_relationship,
                round_data=round_data,
                # FIXME: use activity unique name instead?
                value=activity.pk,
                submitted=True
                )

def get_performed_activity_ids(participant_group_relationship):
    return [prdv.pk for prdv in participant_group_relationship.participant_data_value_set.filter(parameter=get_activity_performed_parameter())]

@receiver(signals.midnight_tick)
def update_active_experiments(sender, time=None, **kwargs):
    for experiment in get_active_experiments():
        # calculate total carbon savings and decide if they move on to the next level
        for group in experiment.group_set.all():
            carbon_footprint_level_grdv = get_carbon_footprint_level(group)
            if should_advance_level(group, carbon_footprint_level_grdv.value):
# advance group level
                carbon_footprint_level_grdv.value = min(carbon_footprint_level_grdv.value + 1, 3)
                carbon_footprint_level_grdv.save()

@receiver(signals.round_started)
def round_started_handler(sender, experiment=None, **kwargs):
    if sender != get_lighterprints_experiment_metadata().pk:
        logger.debug("received invalid signal from sender %s", sender)
        return
    # FIXME: See if we can push this logic up to core..
    current_round_data = experiment.current_round_data
    carbon_footprint_level_parameter = get_carbon_footprint_level_parameter()
# only create the carbon footprint level parameter, the participant activity performed data values will be created each
# time.
    for group in experiment.group_set.all():
        carbon_footprint_level_grdv = current_round_data.group_data_value_set.create(group=group, parameter=carbon_footprint_level_parameter)
        carbon_footprint_level_grdv.value = 1
        carbon_footprint_level_grdv.save()

def get_daily_carbon_savings(group):
# grab all of yesterday's participant data values
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(1)
    total_savings = Decimal(0.0)
    for activity_performed_dv in group.get_participant_data_values(parameter_name='activity_performed').filter(date_created__gte=yesterday):
        activity = Activity.objects.get(pk=activity_performed_dv.value)
        total_savings += activity.savings
    #total = participant_data_values.aggregate(total=Sum('int_value'))['total']
    logger.debug("total carbon savings: %s", total_savings)
    return total_savings

def should_advance_level(group, level, max_level=3, level_multiplier=10):
    if level < max_level:
        daily_carbon_savings = get_daily_carbon_savings(group)
        return daily_carbon_savings > (level * level_multiplier)
    return False

