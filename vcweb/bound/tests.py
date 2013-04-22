"""
Tests for boundary effects experiment
"""
from vcweb.core.tests import BaseVcwebTest
from vcweb.core.models import Parameter
from vcweb.bound.models import *

import logging
logger = logging.getLogger(__name__)


class BaseTest(BaseVcwebTest):
    fixtures = [ 'bound_experiment_metadata', 'forestry_experiment_metadata', 'bound_parameters', ]

    def create_harvest_decisions(self, value=10):
        for pgr in self.experiment.participant_group_relationships:
            logger.debug("setting harvest decision for %s to %s", pgr, value)
            set_harvest_decision(pgr, value, submitted=True)

    def setUp(self, **kwargs):
        super(BaseTest, self).setUp(experiment_metadata=get_experiment_metadata(), **kwargs)
        logger.debug("boundary effects test loaded experiment %s", self.experiment)

class AdjustHarvestDecisionsTest(BaseTest):
    def test_adjust_harvest_decisions(self):
        e = self.experiment
        e.activate()
        for rl in range(30, 40):
            e.start_round()
            self.create_harvest_decisions()
            for g in e.groups:
                set_resource_level(g, rl)
            e.end_round()
            for g in e.groups:
                self.assertEqual(get_resource_level(g), 0)
            for pgr in self.participant_group_relationships:
                self.assertTrue(get_harvest_decision(pgr) <= 8)

class MaxResourceLevelTest(BaseTest):
    def test_max_resource_level(self):
        e = self.experiment
        e.activate()
        self.assertEqual(get_max_resource_level(e.current_round), 5 * 3 * 20)


class InitialDataTest(BaseTest):
    def test_experiment_metadata(self):
        self.assertIsNotNone(get_experiment_metadata())

    def test_parameters(self):
        ps = Parameter.objects.filter(experiment_metadata=get_experiment_metadata())
        expected_parameter_names = ('survival_cost', 'storage', 'player_status')
        for p in ps:
            self.assertTrue(p.name in expected_parameter_names)