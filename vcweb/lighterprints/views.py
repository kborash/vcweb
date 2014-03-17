from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.csrf import csrf_exempt

from vcweb.core.decorators import participant_required
from vcweb.core.forms import (ChatForm, CommentForm, LikeForm, GeoCheckinForm, LoginForm)
from vcweb.core.http import JsonResponse
from vcweb.core.models import (ChatMessage, Comment, Experiment, ParticipantGroupRelationship, ParticipantRoundDataValue, Like)
from vcweb.core.views import dumps, get_active_experiment, set_authentication_token
from vcweb.lighterprints.forms import ActivityForm
from vcweb.lighterprints.models import (
        Activity, GroupScores, ActivityStatusList, do_activity, get_group_activity, can_view_other_groups,
        get_lighterprints_experiment_metadata, get_time_remaining, is_linear_public_good_game,
        )

from datetime import datetime
import logging
logger = logging.getLogger(__name__)

@csrf_exempt
@participant_required
def perform_activity(request):
    form = ActivityForm(request.POST or None)
    logger.debug("performing activity: %s", form)
    if form.is_valid():
        activity_id = form.cleaned_data['activity_id']
        participant_group_id = form.cleaned_data['participant_group_id']
        logger.debug("%s performing activity %s", participant_group_id, activity_id)
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group__experiment'), pk=participant_group_id)
#        latitude = form.cleaned_data['latitude']
#        longitude = form.cleaned_data['longitude']
        if participant_group_relationship.participant == request.user.participant:
            activity = get_object_or_404(Activity, pk=activity_id)
            performed_activity = do_activity(activity=activity, participant_group_relationship=participant_group_relationship)
# perform checkin logic here, query foursquare API for nearest "green" venu
#            logger.debug("searching venues at %s,%s", latitude, longitude)
#            venues = foursquare_venue_search(latitude=latitude, longitude=longitude,
#                    categoryId=','.join(get_foursquare_category_ids()))
#            logger.debug("Found venues: %s", venues)
            if performed_activity is not None:
                return JsonResponse(dumps({
                    'success': True,
                    'viewModel':get_view_model_json(participant_group_relationship)
                    }))
            else:
                message = "Activity was not available at this time"
        else:
            message = "You're not authorized to perform this activity as this person %s" % participant_group_relationship
            logger.warning("authenticated user %s tried to perform activity %s as %s", request.user, activity_id, participant_group_relationship)
    logger.warning("Invalid form, did not perform activity %s", message)
    return JsonResponse(dumps({'success': False, 'response': message}))

@csrf_exempt
@login_required
def post_chat_message(request):
    form = ChatForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        message = form.cleaned_data['message']
        pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user'), pk=participant_group_id)
        if pgr.participant != request.user.participant:
            logger.warning("authenticated user %s tried to post message %s as %s", request.user, message, pgr)
            return JsonResponse(dumps({'success': False, 'message': "Invalid request"}))
        chat_message = ChatMessage.objects.create(value=message, participant_group_relationship=pgr)
        logger.debug("%s: %s", pgr.participant, chat_message)
# FIXME: just get the chat messages
        (team_activity, chat_messages) = get_group_activity(pgr)
        return JsonResponse(dumps({'success': True, 'viewModel': { 'groupActivity': team_activity } }))
    return JsonResponse(dumps({'success': False, 'message': "Invalid chat message post"}))


@csrf_exempt
@login_required
def like(request):
    form = LikeForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        target_id = form.cleaned_data['target_id']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group__experiment'), pk=participant_group_id)
        if participant_group_relationship.participant != request.user.participant:
            logger.warning("authenticated user %s tried to like target_id %s as %s", request.user, target_id, participant_group_relationship)
            return JsonResponse(dumps({'success': False, 'message': "Invalid request"}))
        logger.debug("pgr: %s", participant_group_relationship)
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        logger.debug("target: %s", target)
        # FIXME: either needs a uniqueness constraint to ensure that duplicates don't get created or add guards when we
        # retrieve them to only send back the latest one (feels hacky).  See
        # https://bitbucket.org/virtualcommons/vcweb/issue/59/get_or_create-issues-for-likes
        round_data = participant_group_relationship.current_round_data
        Like.objects.create(round_data=round_data, participant_group_relationship=participant_group_relationship, target_data_value=target)
        logger.debug("Participant %s liked %s", participant_group_relationship, target)
        return JsonResponse(dumps({'success': True, 'viewModel': get_view_model_json(participant_group_relationship)}))
    else:
        logger.debug("invalid form: %s from request: %s", form, request)
        return JsonResponse(dumps({'success': False, 'message': 'Invalid like post'}))

@csrf_exempt
@login_required
def post_comment(request):
    form = CommentForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        target_id = form.cleaned_data['target_id']
        message = form.cleaned_data['message']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group__experiment'), pk=participant_group_id)
        if participant_group_relationship.participant != request.user.participant:
            logger.warning("authenticated user %s tried to post comment %s on target %s as %s", request.user, message, target_id, participant_group_relationship)
            return JsonResponse(dumps({'success': False, 'message': "Invalid request"}))
        target = get_object_or_404(ParticipantRoundDataValue, pk=target_id)
        Comment.objects.create(
                string_value=message,
                round_data=participant_group_relationship.current_round_data,
                participant_group_relationship=participant_group_relationship,
                target_data_value=target)
        logger.debug("Participant %s commented '%s' on %s", participant_group_relationship.participant, message, target)
        return JsonResponse(dumps({'success': True, 'viewModel' : get_view_model_json(participant_group_relationship)}))
    else:
        logger.debug("invalid form: %s from request: %s", form, request)
        return JsonResponse(dumps({'success': False, 'message': 'Invalid post comment'}))


def get_view_model_json(participant_group_relationship, activities=None, experiment=None, round_configuration=None, round_data=None, **kwargs):
    if activities is None:
        activities = Activity.objects.all()
    own_group = participant_group_relationship.group
    if experiment is None:
        experiment = own_group.experiment
    if round_configuration is None:
        round_configuration = experiment.current_round
    if round_data is None:
        round_data = experiment.current_round_data
    compare_other_group = can_view_other_groups(round_configuration=round_configuration)
    linear_public_good = is_linear_public_good_game(round_configuration.experiment_configuration)
    group_scores = GroupScores(experiment, round_data, participant_group_relationship=participant_group_relationship)
    total_participant_points = group_scores.total_participant_points
    group_data = group_scores.get_group_data_list()
    own_group_level = group_scores.get_group_level(own_group)
    activity_status_list = ActivityStatusList(participant_group_relationship, activities, round_configuration, group_level=own_group_level)
    (team_activity, chat_messages) = get_group_activity(participant_group_relationship)
    #(chat_messages, group_activity) = get_group_activity_tuple(participant_group_relationship)
    (hours_left, minutes_left) = get_time_remaining()
    first_visit = participant_group_relationship.first_visit
    if first_visit:
        participant_group_relationship.first_visit = False
        participant_group_relationship.save()
    return dumps({
        'participantGroupId': participant_group_relationship.pk,
        'completed': group_scores.is_completed(own_group),
        'compareOtherGroup': compare_other_group,
        'groupData': group_data,
        'hoursLeft': hours_left,
        'minutesLeft': minutes_left,
        'firstVisit': first_visit,
        # FIXME: extract this from groupData instead..
        'groupLevel': own_group_level,
        'linearPublicGood': linear_public_good,
        'averagePoints': group_scores.average_points(own_group),
        'pointsToNextLevel': group_scores.get_points_goal(own_group),
        'hasScheduledActivities': group_scores.has_scheduled_activities,
        'groupActivity': team_activity,
        'groupName': own_group.name,
        'activities': activity_status_list.activity_dict_list,
        'totalPoints': total_participant_points,
        })

@participant_required
def get_view_model(request, participant_group_id=None):
    if participant_group_id is None:
        # check in the request query parameters as well
        participant_group_id = request.GET.get('participant_group_id')
# FIXME: replace with ParticipantGroupRelationship.objects.fetch(pk=participant_group_id)
    pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group__experiment'), pk=participant_group_id)
    if pgr.participant != request.user.participant:
        # security check to ensure that the authenticated participant is the same as the participant whose data is
        # being requested
        logger.warning("user %s tried to access view model for %s", request.user.participant, pgr)
        raise PermissionDenied("Access denied.")
    view_model_json = get_view_model_json(pgr, experiment=pgr.group.experiment)
    return JsonResponse(dumps({'success': True, 'view_model_json': view_model_json}))

#FIXME: push this into core api/login if possible
def mobile_login(request):
    form = LoginForm(request.POST or None)
    try:
        if form.is_valid():
            user = form.user_cache
            logger.debug("user was authenticated as %s, attempting to login", user)
            auth.login(request, user)
            set_authentication_token(user, request.session.session_key)
            return redirect('lighterprints:mobile_participate')
    except Exception as e:
        logger.debug("Invalid login: %s", e)
    return render(request, 'lighterprints/mobile/login.html')


@participant_required
def mobile_participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_active_experiment(participant, experiment_metadata=get_lighterprints_experiment_metadata())
    pgr = experiment.get_participant_group_relationship(participant)
    all_activities = Activity.objects.all()
    view_model_json = get_view_model_json(pgr, all_activities, experiment)
    return render(request, 'lighterprints/mobile/index.html', {
        'experiment': experiment,
        'participant_group_relationship': pgr,
        'view_model_json': view_model_json,
        'all_activities': all_activities,
        })

@participant_required
def participate(request, experiment_id=None):
    participant = request.user.participant
    experiment = get_object_or_404(Experiment, pk=experiment_id, experiment_metadata=get_lighterprints_experiment_metadata())
    if experiment.is_active:
        round_configuration = experiment.current_round
        pgr = get_object_or_404(ParticipantGroupRelationship.objects.select_related('participant__user', 'group'), participant=participant, group__experiment=experiment)
        compare_other_group = can_view_other_groups(round_configuration=round_configuration)
        all_activities = Activity.objects.all()
        view_model_json = get_view_model_json(pgr, activities=all_activities, experiment=experiment, round_configuration=round_configuration)
#    if request.mobile:
        # FIXME: change this to look up templates in a mobile templates directory?
#        logger.warning("mobile request detected by %s, but we're not ready for mobile apps", participant)
        #return redirect('https://vcweb.asu.edu/devfoot')
        return render(request, 'lighterprints/participate.html', {
            'experiment': experiment,
            'participant_group_relationship': pgr,
            'compare_other_group': compare_other_group,
            'view_model_json': view_model_json,
            'all_activities': all_activities,
        })
    else:
        sd = experiment.start_date
        upcoming = sd > datetime.now().date() if sd is not None else False
        return render(request, 'lighterprints/inactive.html', { 'experiment': experiment, 'upcoming': upcoming })

@participant_required
def checkin(request):
    form = GeoCheckinForm(request.POST or None)
    if form.is_valid():
        participant_group_id = form.cleaned_data['participant_group_id']
        latitude = form.cleaned_data['latitude']
        longitude = form.cleaned_data['longitude']
        participant_group_relationship = get_object_or_404(ParticipantGroupRelationship.objects.select_related('group', 'participant__user'), pk=participant_group_id)
        logger.debug("%s checking at at (%s, %s)", participant_group_relationship, latitude, longitude)
        if request.user.participant == participant_group_relationship.participant:
# perform checkin logic here, query foursquare API for nearest "green" venu
#            venues = foursquare_venue_search(latitude=latitude, longitude=longitude,
#                    categoryId=','.join(get_foursquare_category_ids()))
#            logger.debug("Found venues: %s", venues)
            return JsonResponse(dumps({'success':True}))
        else:
            logger.warning("authenticated user %s tried to checkin at (%s, %s) for %s", request.user, latitude, longitude, participant_group_relationship)
    return JsonResponse(dumps({'success':False, 'message': 'Invalid request'}))
