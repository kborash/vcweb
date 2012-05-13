from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from model_utils.managers import PassThroughManager
from vcweb.core import signals, simplecache, enum
from vcweb.core.models import (Experiment, ExperimentMetadata, Experimenter,
        GroupRoundDataValue, ParticipantGroupRelationship, ParticipantRoundDataValue, Parameter, User)
from vcweb.core.services import fetch_foursquare_categories
import collections
from datetime import datetime, date, time, timedelta
from mptt.models import MPTTModel, TreeForeignKey, TreeManager
import logging
logger = logging.getLogger(__name__)
from brabeion import badges
from brabeion.base import Badge, BadgeAwarded

ActivityStatus = enum('AVAILABLE', 'COMPLETED', 'UNAVAILABLE')

class ActivityBadge(Badge):
    slug = "activity"
    levels = ["Bronze", "Silver", "Gold"]
    events = [ "activity_performed", ]
    multiple = False
    def award(self, **state):
        user = state["user"]
        activity = state["activity"]
        participant_group_relationship = ParticipantGroupRelationship.objects.get(group__experiment=get_lighterprints_public_experiment(),
                participant=user.participant)
        number_of_times_performed = participant_group_relationship.participant_data_value_set.filter(
                parameter=get_activity_performed_parameter()).count()
        if number_of_times_performed < 3:
            return None
        elif number_of_times_performed == 3:
            level = 1
        elif number_of_times_performed == 8:
            level = 2
        elif number_of_times_performed == 15:
            level = 3
        return BadgeAwarded(level=level, slug=activity.name, name=activity.name, description=activity.description)

badges.register(ActivityBadge)


class ActivityQuerySet(models.query.QuerySet):
    """
    for the moment, categorizing Activities as tiered or leveled.  Leveled activities are used in experiments, where
    groups advance in level and each level comprises a set of activities.  Tiered activities are used in the open
    lighterprints experiment, where mastering one activity can lead to another set of activities
    """
    def for_public_experiment(self, participant_group_relationship=None, **kwargs):
        return self.filter(is_public=True)

class ActivityManager(TreeManager, PassThroughManager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Activity(MPTTModel):
    name = models.CharField(max_length=32, unique=True)
    display_name = models.CharField(max_length=64, null=True, blank=True)
    summary = models.CharField(max_length=256)
    description = models.TextField()
    url = models.URLField()
    savings = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    points = models.PositiveIntegerField(default=0)
    available_all_day = models.BooleanField(default=False)
    personal_benefits = models.TextField(null=True, blank=True)
# FIXME: allow for experiment-configurable levels?
    level = models.PositiveIntegerField(default=1)
    group_activity = models.BooleanField(default=False, help_text='Whether or not this activity has beneficial group effect multipliers, e.g., ride sharing')
# currently unused
    cooldown = models.PositiveIntegerField(default=1, null=True, blank=True, help_text='How much time, in hours, must elapse before this activity can become available again')
    icon = models.ImageField(upload_to='lighterprints/activity-icons/')
# for user submitted activities
    creator = models.ForeignKey(User, null=True)
    date_created = models.DateTimeField(default=datetime.now)
    last_modified = models.DateTimeField(default=datetime.now)
# for the "in-the-wild" app, activities unlock other sets of activities in a tree-like fashion
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children_set')
    is_public = models.BooleanField(default=False)

    objects = ActivityManager.for_queryset_class(ActivityQuerySet)()

    @property
    def label(self):
        return self.display_name if self.display_name else self.name

    @property
    def icon_name(self):
        return self.name

    @property
    def icon_url(self):
        return self.icon.url if self.icon else ""

    def to_dict(self, attrs=('pk', 'name', 'summary', 'display_name', 'description', 'savings', 'url', 'available_all_day', 'level', 'icon_url', 'personal_benefits', 'points')):
        activity_as_dict = {}
        for attr_name in attrs:
            activity_as_dict[attr_name] = getattr(self, attr_name, None)
        return activity_as_dict

    def __unicode__(self):
        return u'%s (+%s)' % (self.label, self.points)

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
def get_foursquare_category_ids(parent_category_name='Travel', subcategory_names=['Light Rail', 'Bike', 'Bus Station', 'Train Station']):
    categories = fetch_foursquare_categories()
    for parent_category in categories:
        if parent_category_name in parent_category['name']:
            return [subcategory['id'] for subcategory in parent_category['categories'] if subcategory['shortName'] in subcategory_names]

@simplecache
def get_lighterprints_public_experiment():
    # FIXME: hacky
    return Experiment.objects.filter(experiment_metadata=get_lighterprints_experiment_metadata(),
            experiment_configuration__is_public=True)[0]

@simplecache
def get_lighterprints_experiment_metadata():
    return ExperimentMetadata.objects.get(namespace='lighterprints')

def create_activity_performed_parameter(experimenter=None):
    if experimenter is None:
        experimenter = Experimenter.objects.get(pk=1)
    parameter, created = Parameter.objects.get_or_create(name='activity_performed', scope=Parameter.PARTICIPANT_SCOPE, type='foreignkey',
            creator=experimenter, experiment_metadata=get_lighterprints_experiment_metadata())
    if created: logger.debug("created activity performed parameter %s", parameter)
    return parameter

@simplecache
def get_activity_unlocked_parameter():
    return Parameter.objects.get(name='activity_unlocked')

@simplecache
def get_activity_performed_parameter():
    return Parameter.objects.get(name='activity_performed')

@simplecache
def get_footprint_level_parameter():
    return Parameter.objects.get(name='footprint_level')

def get_footprint_level(group):
    return GroupRoundDataValue.objects.get(group=group, parameter=get_footprint_level_parameter())

def get_active_experiments():
    return Experiment.objects.filter(experiment_metadata=get_lighterprints_experiment_metadata(),
            status__in=('ACTIVE', 'ROUND_IN_PROGRESS'))


# returns a tuple of (flattened_activities list + activity_by_level dict)
def get_all_available_activities(participant_group_relationship, all_activities=None):
    if all_activities is None:
        all_activities = Activity.objects.all()
    flattened_activities = []
    activity_by_level = collections.defaultdict(list)

    for activity in all_activities:
        activity_by_level[activity.level].append(activity)
        activity_as_dict = activity.to_dict()
        try:
            activity_as_dict['availabilities'] = [availability.to_dict() for availability in ActivityAvailability.objects.filter(activity=activity)]
            activity_as_dict['available'] = is_activity_available(activity, participant_group_relationship)
            activity_as_dict['time_slots'] = ','.join([av.time_slot for av in activity.availability_set.all()])
        except Exception as e:
            logger.debug("failed to get authenticated activity list: %s", e)
        flattened_activities.append(activity_as_dict)
    return (flattened_activities, activity_by_level)

def available_activities(activity=None):
    current_time = datetime.now().time()
    available_time_slot = dict(start_time__lte=current_time, end_time__gte=current_time)
    if activity is not None:
        available_time_slot['activity'] = activity
    activities = [activity_availability.activity for activity_availability in ActivityAvailability.objects.select_related(depth=1).filter(Q(**available_time_slot))]
    logger.debug("activities: %s", activities)
    activities.extend(Activity.objects.filter(available_all_day=True))
    return activities

def check_public_activity_availability(activity, participant_group_relationship):
    '''
    in the public lighterprints game, an unlocked activity data value is created whenever a new activity is unlocked signifying that the given Activity is now available to
    the user
    '''
    available_activity_ids = participant_group_relationship.participant_data_value_set.filter(parameter=get_activity_unlocked_parameter()).values_list('int_value', flat=True)
    return activity.pk in available_activity_ids and not is_already_performed_today(activity, participant_group_relationship)

def is_already_performed_today(activity, participant_group_relationship):
    today = datetime.combine(date.today(), time())
    already_performed = participant_group_relationship.participant_data_value_set.filter(parameter=get_activity_performed_parameter(),
            int_value=activity.id,
            date_created__gt=today)
    return ActivityStatus.AVAILABLE if already_performed.count() == 0 else ActivityStatus.COMPLETED


def check_activity_availability(activity, participant_group_relationship, **kwargs):
    if participant_group_relationship.group.experiment.is_public:
        return check_public_activity_availability(activity, participant_group_relationship)

    '''
    FIXME: see if we can simplify or split up
    how often can a participant participate in an activity? whenever it falls within the ActivityAvailability schedule
    and if the participant hasn't already performed this activity during a one-day cycle (which begins at midnight)
    '''
    level = get_footprint_level(participant_group_relationship.group).value
    if activity.level > level:
        logger.debug("activity %s had larger level (%s) than group level (%s)", activity, activity.level, level)
        return ActivityStatus.UNAVAILABLE
    elif activity.available_all_day:
        # check if they've done it already today, check if the combine is necessary
        activity_status = is_already_performed_today(activity, participant_group_relationship)
        logger.debug("activity is available all day, was it already performed? %s", activity_status)
        return activity_status
    else:
        now = datetime.now()
        current_time = now.time()
        # FIXME: check if this participant has already participated in this activity within this particular interval (for all
        # day, today, for time slots, during this particular time slot). There should only be one availability
        try:
            logger.debug("checking availability set %s", activity.availability_set.all())
            availabilities = activity.availability_set.filter(start_time__lte=current_time, end_time__gte=current_time)
            if availabilities.count() > 0:
                earliest_start_time = datetime.combine(date.today(), availabilities[0].start_time)
                logger.debug("earliest start time: %s", earliest_start_time)
                already_performed = ParticipantRoundDataValue.objects.filter(parameter=get_activity_performed_parameter(),
                        participant_group_relationship=participant_group_relationship,
                        int_value=activity.pk,
                        date_created__range=(earliest_start_time, now))
                return ActivityStatus.AVAILABLE if already_performed.count() == 0 else ActivityStatus.COMPLETED
        except Exception as e:
            logger.debug("exception while checking if this activity had already been performed by this participant: %s", e)
# default behavior is for the activity to be unavailable
    return ActivityStatus.UNAVAILABLE

def is_activity_available(activity, participant_group_relationship):
    return check_activity_availability(activity, participant_group_relationship) == ActivityStatus.AVAILABLE

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
    logger.debug("updating active experiments")
    for experiment in get_active_experiments():
        # calculate total carbon savings and decide if they move on to the next level
        for group in experiment.group_set.all():
            footprint_level_grdv = get_footprint_level(group)
            if should_advance_level(group, footprint_level_grdv.value):
# advance group level
                footprint_level_grdv.value = min(footprint_level_grdv.value + 1, 3)
                footprint_level_grdv.save()

@receiver(signals.round_started)
def round_started_handler(sender, experiment=None, **kwargs):
    if sender != get_lighterprints_experiment_metadata().pk:
        return
    # FIXME: See if we can push this logic up to core..
    current_round_data = experiment.current_round_data
    footprint_level_parameter = get_footprint_level_parameter()
# only create the carbon footprint level parameter, the participant activity performed data values will be created each
# time.
    for group in experiment.group_set.all():
        footprint_level_grdv = current_round_data.group_data_value_set.create(group=group, parameter=footprint_level_parameter)
        footprint_level_grdv.value = 1
        footprint_level_grdv.save()

def average_points_per_person(group):
    return get_group_score(group)[0]

# returns a tuple of the average points per person and the total savings for
# the given group
def get_group_score(group, start=None, end=None):
    if start is None or end is None:
        start = date.today()
        end = start + timedelta(1)
    # establish date range
    # grab all of yesterday's participant data values, starting at 00:00:00 (midnight)
    total_points = 0
# FIXME: is it possible to convert this into an aggregate Sum, e.g., Activity.objects.filter(id__in=[id1, id2, ...]).aggregate(Sum('points'))
# we'd need to a subselect to generate the idlist though
    for activity_performed_dv in group.get_participant_data_values(parameter=get_activity_performed_parameter()).filter(date_created__range=(start, end)):
        activity = activity_performed_dv.value
        total_points += activity.points
    average = total_points / group.size
    logger.debug("total carbon savings: %s divided by %s members = %s per person", total_points, group.size,
            average)
    return (average, total_points)

def points_to_next_level(level, level_multiplier=100):
    return level * level_multiplier

def should_advance_level(group, level, max_level=3):
    if level < max_level:
        return average_points_per_person(group) >= points_to_next_level(level)
    return False

def get_green_points(participant_group_relationship):
    performed_activities = participant_group_relationship.participant_data_value_set.filter(parameter=get_activity_performed_parameter())
    total_points = 0
    for activity_performed_dv in performed_activities:
        total_points += activity_performed_dv.value.points
    return total_points

def get_level(points=0):
    if points < 100:
        return 1
    elif points < 250:
        return 2
    elif points < 400:
        return 3
    elif points < 600:
        return 4
    elif points < 800:
        return 5
    elif points < 1000:
        return 6
    elif points < 1250:
        return 7
    elif points < 1500:
        return 8
    elif points < 2000:
        return 9
    elif points < 2500:
        return 10
    elif points < 3000:
        return 11
    elif points < 3500:
        return 12
    elif points < 4000:
        return 13
    elif points < 4500:
        return 14
    elif points < 5000:
        return 15
    elif points < 5500:
        return 16
    elif points < 6000:
        return 17
    elif points < 6500:
        return 18
    elif points < 7000:
        return 19
    else:
        return 20
