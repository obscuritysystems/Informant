from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.utils import timezone
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from django.template import Context, loader
from django.template import RequestContext
from django.shortcuts import render_to_response
from lookup.forms import *
from lookup.models import *
from bs4 import BeautifulSoup
import urllib
import pycurl
import json
import StringIO
import re
import sys



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
                return HttpResponseRedirect('/member/')
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
                    
                return HttpResponseRedirect('/show_group/'+str(new_group.id))
        else:
            form = CreateGroupForm()
            variables = RequestContext(request,{'form':form})
            return render_to_response('lookup/create_group.html',variables)
        
def show_group(request, group_id):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/')
    else:
        entries  = PersonEntry.objects.raw('select * from lookup_personentry where search_group_id = %s' 
                                               % (group_id) )
        searches = SearchAttempt.objects.raw('select * from lookup_searchattempt where  search_group_id = %s' 
                                               % (group_id))
        form = SearchAttemptForm(initial={'group_id': group_id})
        variables   = RequestContext(request,{'form':form,'entries':entries,'searches':searches})
        return render_to_response('lookup/show_group.html',variables)

def logout_page(request):
  logout(request)
  return HttpResponseRedirect('/')

def run_search(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/')
    else:
        if request.method == 'POST':
            form = SearchAttemptForm(request.POST)
            if form.is_valid():
                search_name = form.cleaned_data['search_name']
                group_id    = form.cleaned_data['group_id']
                sg = SearchGroup.objects.get(pk=group_id)
                
                new_search  = SearchAttempt(search_name=search_name,
                                            create_time=timezone.now(),
                                            user=request.user,
                                            search_group=sg,
                                            )
                new_search.save()   
                entries  = PersonEntry.objects.raw('select * from lookup_personentry where search_group_id = %s' 
                                               % (group_id) )
                lookup_results = []
                for entry in entries:
                    lookup_result = lookup(entry)    
                    if lookup_result is not None:
                        for result in lookup_result:
                            lookup_results.append(result)
                
                #return HttpResponse(lookup_results)
                for result in lookup_results:
                    pr = PersonResult(first_name = result['name'],
                                          phone=result['phone_number'],
                                          search_group=sg,
                                          search_attempt=new_search
                                        )
                    pr.save()
                   
                return HttpResponseRedirect('/show_search/'+str(new_search.id))
                

def show_search(request,search_id):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/')
    else:
        search_results = SearchAttempt.objects.raw('select * from lookup_personresult where search_attempt_id = %s' % (search_id))
        variables   = RequestContext(request,{'search_results':search_results})
        return render_to_response('lookup/show_search.html',variables)



def lookup(entry):

    results = []
    c = pycurl.Curl()
    url = 'http://411.info/people/?'
    attr = urllib.urlencode({'fn':'','ln':entry.first_name,'cz':entry.address})
    url = url + attr
    f = open('/tmp/url','a')
    f.write(str(url)+'\n')
    f.close()
    c.setopt(c.URL, url)
    c.setopt(c.CONNECTTIMEOUT, 5)
    c.setopt(pycurl.FOLLOWLOCATION, 1)
    c.setopt(c.TIMEOUT, 8)
    b = StringIO.StringIO()
    c.setopt(c.COOKIEFILE, '') 
    c.setopt(c.FAILONERROR, True)
    c.setopt(c.HTTPHEADER, ['Accept: application/html', 'Content-Type: application/x-www-form-urlencoded'])
    c.setopt(pycurl.WRITEFUNCTION, b.write)
    try:
        c.perform()
        html_doc = b.getvalue()
        soup = BeautifulSoup(html_doc)
        #todo parse this better
        divs = soup.find_all('div')
        result = {}
        for div in divs:
            if div.get('class'):
                if div['class'][0] == 'cname':
                    result['name'] = div.string
                if div['class'][0] == 'phone':
                    result['phone_number'] = div.string
                    results.append(result)
                    result = {}

        if len(results) == 0:           
            return None
        else:
            return results

    except pycurl.error, error:
        errno, errstr = error
        print 'An error occurred: ', errstr

