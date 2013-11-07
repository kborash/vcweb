import autocomplete_light
from django import forms
from django.forms import widgets
from vcweb.core.autocomplete_light_registry import InstitutionAutocomplete
from vcweb.core.forms import NumberInput
from django.utils.translation import ugettext_lazy as _

import logging

logger = logging.getLogger(__name__)


REQUIRED_ATTRIBUTES = {'class': 'required'}
HOUR_CHOICES = (('0', '0'),('1', '1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7'),('8','8'),('9','9'),('10','10'),('11','11'),('12','12'),('13','13'),('14','14'),('15','15'),('16','16'),('17','17'),('18','18'),('19','19'),('20','20'),('21','21'),('22','22'),('23','23'))
MIN_CHOICES = (('0','0'),('15','15'),('30','30'),('45','45'))
ATTENDANCE_CHOICES = (('0', 'participated'), ('1', 'absent'), ('2', 'turned away'), ('3', 'select'))


class SessionForm(forms.Form):
    pk = forms.IntegerField(widgets.TextInput())
    experiment_metadata_pk = forms.IntegerField(widgets.TextInput(), required=False)
    start_date = forms.CharField(widget=widgets.TextInput(), required=False)
    start_hour = forms.ChoiceField(choices=HOUR_CHOICES, required=False)
    start_min = forms.ChoiceField(choices=MIN_CHOICES, required=False)
    end_date = forms.CharField(widget=widgets.TextInput(), required=False)
    end_hour = forms.ChoiceField(choices=HOUR_CHOICES, required=False)
    end_min = forms.ChoiceField(choices=MIN_CHOICES, required=False)
    capacity = forms.IntegerField(widget=widgets.TextInput(), required=False)
    location = forms.CharField(widget=widgets.TextInput(), required=False)
    request_type = forms.CharField(widget=widgets.TextInput())

    def clean(self):
        data = super(forms.Form, self).clean()
        pk = data.get('pk')
        experiment_metadata_pk = data.get('experiment_metadata_pk')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        location = data.get('location')
        request_type = data.get('request_type')

        if not pk:
            raise forms.ValidationError(_("Invalid Experiment session PK"))
        else:
            logger.debug(data)
            if request_type != 'delete':
                if not experiment_metadata_pk or not start_date or not end_date:
                    raise forms.ValidationError(_("Please Fill Start date or End date"))
                if not location:
                    raise forms.ValidationError(_("Please Enter location for the Experiment Session"))
        return data


class SessionInviteForm(forms.Form):
    no_of_people = forms.IntegerField(widget=NumberInput(attrs={'value': 50, 'class': 'input-mini'}))
    affiliated_university = forms.CharField(widget=autocomplete_light.TextWidget(InstitutionAutocomplete))
    invitation_subject = forms.CharField(widget=widgets.TextInput())
    invitation_text = forms.CharField(widget=widgets.Textarea(attrs={'rows': '4'}))

class SessionAttendanceForm(forms.Form):
    READONLY_FIELDS = ('first_name', 'last_name', 'email', 'major', 'class_status')

    pk = forms.IntegerField(widget=widgets.HiddenInput())
    first_name = forms.CharField(widget=widgets.TextInput())
    last_name = forms.CharField(widget=widgets.TextInput())
    email = forms.CharField(widget=widgets.TextInput())
    major = forms.CharField(widget=widgets.TextInput())
    class_status = forms.CharField(widget=widgets.TextInput())
    attendance = forms.ChoiceField(choices=ATTENDANCE_CHOICES)

    def __init__(self, *args, **kwargs):
         instance = kwargs.get('instance')
         if instance is not None:
            super(SessionAttendanceForm, self).__init__(*args, **kwargs)
            for field in self.READONLY_FIELDS:
                self.fields[field].widget.attrs['readonly'] = True
         else:
            super(SessionAttendanceForm, self).__init__(*args, **kwargs)



