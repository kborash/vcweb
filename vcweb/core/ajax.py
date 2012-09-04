from django.http import HttpResponse
from django.template.loader_tags import BlockNode, ExtendsNode
from django.template import loader, Context, RequestContext
from django.shortcuts import get_object_or_404

from vcweb.core.decorators import experimenter_required, dajaxice_register
from vcweb.core.models import Experiment
from vcweb.core.views import dumps

import logging
logger = logging.getLogger(__name__)

def get_template(template):
    if isinstance(template, (tuple, list)):
        return loader.select_template(template)
    return loader.get_template(template)

class BlockNotFound(Exception):
    pass

def render_template_block(template, block, context):
    """
    Renders a single block from a template. This template should have previously been rendered.
    """
    return render_template_block_nodelist(template.nodelist, block, context)

def render_template_block_nodelist(nodelist, block, context):
    for node in nodelist:
        if isinstance(node, BlockNode) and node.name == block:
            return node.render(context)
        for key in ('nodelist', 'nodelist_true', 'nodelist_false'):
            if hasattr(node, key):
                try:
                    return render_template_block_nodelist(getattr(node, key), block, context)
                except:
                    pass
    for node in nodelist:
        if isinstance(node, ExtendsNode):
            try:
                return render_template_block(node.get_parent(context), block, context)
            except BlockNotFound:
                pass
    raise BlockNotFound

def render_block_to_string(template_name, block, dictionary=None, context_instance=None):
    """
    Loads the given template_name and renders the given block with the given dictionary as
    context. Returns a string.
    """
    dictionary = dictionary or {}
    t = get_template(template_name)
    if context_instance:
        context_instance.update(dictionary)
    else:
        context_instance = Context(dictionary)
    t.render(context_instance)
    return render_template_block(t, block, context_instance)

def direct_block_to_template(request, template, block, extra_context=None, mimetype=None, **kwargs):
    """
    Render a given block in a given template with any extra URL parameters in the context as
    ``{{ params }}``.
    """
    if extra_context is None:
        extra_context = {}
    dictionary = {'params': kwargs}
    for key, value in extra_context.items():
        if callable(value):
            dictionary[key] = value()
        else:
            dictionary[key] = value
    c = RequestContext(request, dictionary)
    t = get_template(template)
    t.render(c)
    return HttpResponse(render_template_block(t, block, c), mimetype=mimetype)

def _get_experiment(request, pk):
    experiment = get_object_or_404(Experiment, pk=pk)
    if request.user.experimenter == experiment.experimenter:
        return experiment
    raise Experiment.DoesNotExist("Sorry, %s - you do not have access to experiment %s" % (experiment.experimenter, pk))

def _render_experiment_monitor_block(block, experiment, request):
    return render_block_to_string('experimenter/monitor.html', block, { 'experiment': experiment },
            context_instance=RequestContext(request))

@experimenter_required
@dajaxice_register
def get_experiment_model(request, pk):
    experiment = _get_experiment(request, pk)
    return dumps({
        'roundStatusLabel': experiment.get_status_display(),
        'roundSequenceLabel': experiment.sequence_label,
        'timeRemaining': experiment.time_remaining,
        'roundData': experiment.round_data_set.all(),
        'chatMessages': experiment.all_chat_messages.all(),
        'messages': experiment.activity_log_set.all(),
        })

@experimenter_required
@dajaxice_register
def experiment_controller(request, pk, action=''):
    experiment = _get_experiment(request, pk)
    try:
        experiment.invoke(action)
    except AttributeError as e:
        logger.warning("no attribute %s on experiment %s (%s)", action, experiment.status_line, e)
    return dumps({
        'experiment': experiment,
        })
    """
    status_block = _render_experiment_monitor_block('status', experiment, request)
    data_block = _render_experiment_monitor_block('data', experiment, request)
    transition_url = None
    should_transition = action in ('start_round', 'end_round', 'advance_to_next_round')
    if should_transition:
        transition_url = 'wait' if action == 'end_round' else 'participate'
    return simplejson.dumps({
        'should_transition': should_transition,
        'transition_url': transition_url,
        'status': status_block,
        'experimentData': data_block,
        'active_round_number': experiment.current_round_sequence_number,
        'round_data_count': experiment.round_data_set.count(),
        'error_message': error_message,
        })
    """
