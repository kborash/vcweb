from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.forms import widgets, ValidationError
from django.utils.translation import ugettext_lazy as _

from vcweb.core.models import Participant, Experimenter

from django.core.validators import email_re

import re

REQUIRED_EMAIL_ATTRIBUTES = { 'class' : 'required email' }
REQUIRED_ATTRIBUTES = { 'class' : 'required' }

class RegistrationForm(forms.Form):
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    confirm_password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    first_name = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    last_name = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))
    institution = forms.CharField(widget=widgets.TextInput(attrs=REQUIRED_ATTRIBUTES))

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            return email
        raise forms.ValidationError(_("This email address is already in our system."))

    def clean_confirm_password(self):
        password = self.cleaned_data['password']
        confirm_password = self.cleaned_data['confirm_password']
        if password != confirm_password:
            raise forms.ValidationError(_("Please make sure your passwords match."))
        return self.confirm_password

class LoginForm(forms.Form):
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        if email and password:
            self.user_cache = authenticate(username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_("Your combination of email and password was incorrect."))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This user has been deactivated. Please contact us if this is in error."))
        return self.cleaned_data

class ParticipantAccountForm(forms.ModelForm):
    email = forms.EmailField(widget=widgets.TextInput(attrs=REQUIRED_EMAIL_ATTRIBUTES))
    password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))
    confirm_password = forms.CharField(widget=widgets.PasswordInput(attrs=REQUIRED_ATTRIBUTES))

    class Meta:
        model = Participant

class ExperimenterAccountForm(forms.ModelForm):
    class Meta:
        model = Experimenter

email_separator_re = re.compile(r'[^\w\.\-\+@_]+')
class EmailListField(forms.CharField):
    widget = forms.Textarea
    def clean(self, value):
        super(EmailListField, self).clean(value)
        emails = email_separator_re.split(value)
        if not emails:
            raise ValidationError(_(u'You must enter at least one email address.'))
        for email in emails:
            if not email_re.match(email):
                raise ValidationError(_(u'%s is not a valid email address.' % email))
        return emails

class RegisterParticipantsForm(forms.ModelForm):
    experiment_pk = forms.IntegerField(widget=widgets.HiddenInput)
    experiment_passcode = forms.CharField(min_length=3, label="Experiment passcode")
    institution_name = forms.CharField(min_length=3,label="Institution name")
    institution_url = forms.CharField(min_length=3,label='Institution URL')

class RegisterSimpleParticipantsForm(RegisterParticipantsForm):
    email_suffix = forms.CharField(min_length='3')
    number_of_participants = forms.IntegerField(min_value=1)

class RegisterEmailListParticipantsForm(RegisterParticipantsForm):
    participant_emails = EmailListField(label="Participant emails")

class QuizForm(forms.Form):
    name_question = forms.CharField(max_length=64, label="What is your name?")
    def __init__(self, *args, **kwargs):
        quiz_questions = []
        try:
            quiz_questions = kwargs.pop('quiz_questions')
        finally:
            super(QuizForm, self).__init__(*args, **kwargs)
            for quiz_question in quiz_questions:
                self.fields['quiz_question_%d' % quiz_question.pk] = forms.CharField(label=quiz_question.label)

    def extra_questions(self):
        for name, value in self.cleaned_data.items():
            if name.startswith('quiz_question_'):
                yield (self.fields[name].label, value)

