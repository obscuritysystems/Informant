import re
from django import forms as forms
from django.contrib.auth.models import User


class RegistrationForm(forms.Form):
  username = forms.CharField(label='Username', max_length=30)
  email = forms.EmailField(label='Email')
  password1 = forms.CharField(
    label='Password',
    widget=forms.PasswordInput()
  )
  password2 = forms.CharField(
    label='Password (Again)',
    widget=forms.PasswordInput()
  )

  def clean_username(self):
    username = self.cleaned_data['username']
    if not re.search(r'^\w+$', username):
      raise forms.ValidationError('Username can only contain alphanumeric characters and the underscore.')
    try:
      User.objects.get(username=username)
    except:
      return username
    raise forms.ValidationError('Username is already taken.')

  def clean_password2(self):
    if 'password1' in self.cleaned_data:
      password1 = self.cleaned_data['password1']
      password2 = self.cleaned_data['password2']
      if password1 == password2:
        return password2
    raise forms.ValidationError('Passwords do not match.')


class LoginForm(forms.Form):
  username = forms.CharField(label='Username', max_length=30)
  password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput()
  )
 
class CreateGroupForm(forms.Form):
    group_name = forms.CharField(widget=forms.TextInput(attrs={'size':'40'}))
    names       = forms.CharField(label='Names',
                                    widget=forms.Textarea(attrs={'rows':50,'cols':50})
                                  )
    addresses   = forms.CharField(label='Addressses',
                                  widget=forms.Textarea(attrs={'rows':50,'cols':50})
                                )

class SearchAttemptForm(forms.Form):
    search_name = forms.CharField(widget=forms.TextInput(attrs={'size':'40'}))
    group_id = forms.IntegerField(widget=forms.HiddenInput()) 
