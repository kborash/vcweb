"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.

"""

from django.test import TestCase
from vcweb.core.models import Participant, Experiment, Group
import logging

logger = logging.getLogger('vcweb.core.tests')

class VcwebTest(TestCase):
    fixtures = ['test_users_participants', 'forestry_test_data']

    def setUp(self):
        self.participants = Participant.objects.all()
        self.experiment = Experiment.objects.get(pk=1)
        self.group_of_10 = Group(number=1, max_size=10, experiment=self.experiment)
        self.group2 = Group(number=2, experiment=self.experiment)

    class Meta:
        abstract = True

class ExperimentTest(VcwebTest):
    def test_allocate_groups(self):
        self.experiment.allocate_groups(randomize=False)
        self.failUnlessEqual(self.experiment.groups.count(), 2, "should be 2 groups after non-randomized allocation")
        for p in self.participants:
            participant_number = p.get_participant_number(self.experiment)
            self.failIf(participant_number <= 0 or participant_number > p.get_group(self.experiment))




    def test_get_participant_number(self):
        self.experiment.allocate_groups()
        self.failUnlessEqual(self.experiment.groups.count(), 2, "Should have two groups after allocation")
        for p in self.participants:
            participant_number = p.get_participant_number(self.experiment)
            self.failUnless(participant_number > 0, 'participant number should be greater than 0')
            logger.debug("participant number %i (id: %i)" % (participant_number, p.pk))

class GroupTest(VcwebTest):
    def test_group_add(self):
        """
        Tests get_participant_number after groups have been assigned
        """
        g = self.group_of_10
        count = 0;
        for p in self.participants:
            g.add_participant(p)
            count += 1
            self.assertTrue(g.participants)
            self.failUnlessEqual(g.participants.count(), count, "group.participants should be of size 1")
            self.failUnlessEqual(g.size, count, "group size should be 1")


