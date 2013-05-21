from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from django.template import Context, loader
from django.template import RequestContext
from django.shortcuts import render_to_response
from lookup.forms import *
from lookup.models import *

from datetime import datetime  
import time

def index(request):
    if not request.user.is_authenticated():
        return render_to_response('lookup/index.html', RequestContext(request))
    else:
        search_groups = SearchGroup.objects.all()
        return HttpResponseRedirect('/member/')

def member(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/')
    else:
        #groups = SearchGroup.objects.raw('select * from lookup_searchgroup')
        groups = SearchGroup.objects.all()
        #return HttpResponse(str(groups))
        data = {'groups':groups}
        return render_to_response('lookup/member.html', RequestContext(request,data))

def login(request):
    if request.method == 'POST':
        user_name = request.POST['username']
        u_password = request.POST['password']
        user = authenticate(username=user_name, password=u_password)
        if user is not None:
            if user.is_active:
                auth_login(request,user)
                message = "You provided a correct username and password!"
                form = LoginForm()
                variables = RequestContext(request, {'form': form,'message':message})
                return render_to_response('lookup/member.html',variables)
            else:
                message = "Your account has been disabled!"
                form = LoginForm()
                variables = RequestContext(request, {'form': form,'message':message})
                return render_to_response('lookup/login.html',variables)
        else:
            message = "Your username and password were incorrect."
            form = LoginForm()
            variables = RequestContext(request, {'form': form,'message':message})
            return render_to_response('lookup/login.html',variables)
    else:
        form = LoginForm()
        variables = RequestContext(request, {'form': form})
        return render_to_response('lookup/login.html',variables)

def create_group(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/')
    else:
        if request.method == 'POST':
            form = CreateGroupForm(request.POST)
            if form.is_valid():
                group_name       = form.cleaned_data['group_name']
                names            = form.cleaned_data['names']
                addresses        = form.cleaned_data['addresses']
                parsed_names     = names.rstrip().split('\n')
                parsed_addresses = addresses.rstrip().split('\n')

                new_group = SearchGroup(group_name=group_name)
                new_group.save()

                if len(parsed_names) != len(parsed_addresses):
                    return HttpResponse('Address do not match up to names')

                entries = []
                i = 0
                for name in parsed_names:
                    name_add = {'name':name,'address':''}
                    entries.append(name_add)
                for address in parsed_addresses:
                    if i < len(entries):
                        entries[i]['address'] = address
                        i = 1 + i

                for entry in entries:
                    new_person = PersonEntry(first_name=entry['name'].strip(),
                                             address=entry['address'].strip(),
                                             search_group=new_group
                                            )
                    new_person.save()
                    
                variables = RequestContext(request,{'entries':entries})
                return render_to_response('lookup/show_group.html',variables)
        else:
            form = CreateGroupForm()
            variables = RequestContext(request,{'form':form})
            return render_to_response('lookup/create_group.html',variables)
        
def logout_page(request):
  logout(request)
  return HttpResponseRedirect('/')
