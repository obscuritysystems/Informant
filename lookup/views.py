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
from django.db import connection, transaction
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
                zipcodes         = form.cleaned_data['zipcodes']

                parsed_names     = names.rstrip().split('\n')
                parsed_addresses = addresses.rstrip().split('\n')
                parsed_zipcodes  = zipcodes.rstrip().split('\n')

                if len(parsed_names) != len(parsed_addresses):
                    return HttpResponse('The number of addresses and names are not equal')
                if len(parsed_zipcodes) != len(parsed_names):
                    return HttpResponse('The number of zipcodes and names are not equal')
                if len(parsed_zipcodes) != len(parsed_addresses):
                    return HttpResponse('The number of zipcodes and addresses are not equal')


                new_group = SearchGroup(group_name=group_name)
                new_group.save()

                entries = []
                for name in parsed_names:
                    name_split = name.strip().split(' ')
                    name_add = {'last_name':name_split.pop(),'address':'','zipcode':''}
                    entries.append(name_add)
               
                i = 0
                for zipcode in parsed_zipcodes:            
                    zip = regex_zipcode(zipcode.strip())
                    entries[i]['zipcode'] = zip
                    i = 1 + i
                    
                i = 0
                for address in parsed_addresses:
                        entries[i]['address'] = address
                        i = 1 + i
                    

                for entry in entries:
                    new_person = PersonEntry(last_name=entry['last_name'].strip(),
                                             address=entry['address'].strip(),
                                              zipcode=entry['zipcode'].strip(),
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
                            result['entry'] = entry
                            lookup_results.append(result)
                
                #return HttpResponse(lookup_results)
                for result in lookup_results:
                    pr = PersonResult(first_name = result['name'],
                                          phone=result['phone_number'],
                                          search_url=result['url'],
                                          search_group=sg,
                                          search_attempt=new_search,
                                          person_entry=result['entry'],
                                        )
                    pr.save()
                   
                return HttpResponseRedirect('/show_search/'+str(new_search.id))
                

def show_search(request,search_id):
    if not request.user.is_authenticated():
        return HttpResponseRedirect('/')
    else:
        #search_results = SearchAttempt.objects.raw('select * from lookup_personresult where search_attempt_id = %s' % (search_id))
        cursor = connection.cursor()
        cursor.execute('select lookup_personresult.first_name,'+
                                                   'lookup_personresult.phone, '+
                                                   'address, '+
                                                   'lookup_personentry.zipcode,'+
                                                   'lookup_personresult.search_url '+
                                                   'from lookup_personresult '+
                                                   'join lookup_personentry on lookup_personentry.id = lookup_personresult.person_entry_id '+
                                                    'where search_attempt_id = %s', [search_id])
        search_results = cursor.fetchall()

        #return HttpResponse('result' + str(search_results))
        variables   = RequestContext(request,{'search_results':search_results})
        return render_to_response('lookup/show_search.html',variables)


def regex_zipcode(data):
    regex = '^([a-zA-Z]{2})([0-9]{5})([-])*([0-9]{4})?$'
    matchObj = re.match(regex,data, re.M|re.I)

    if matchObj:
        return matchObj.group(2)
    else:
        return None


def lookup(entry):

    results = []
    c = pycurl.Curl()
    url = 'http://411.info/people/?'
    attr = urllib.urlencode({'fn':'','ln':entry.last_name,'cz':str(entry.address) + ' '+ str(entry.zipcode) })
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
                    result['url'] = url
                    results.append(result)
                    result = {}

        if len(results) == 0:           
            return None
        else:
            return results

    except pycurl.error, error:
        errno, errstr = error
        print 'An error occurred: ', errstr

