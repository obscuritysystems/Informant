from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# Create your models here.
class SearchGroup(models.Model):
    group_name =  models.CharField(max_length=254)

class SearchAttempt(models.Model):
    search_name     = models.CharField(max_length=254)
    create_time     = models.DateTimeField('created date')
    user            = models.ForeignKey(User)
    search_group    = models.ForeignKey(SearchGroup)

class PersonEntry(models.Model):
    first_name      = models.CharField(max_length=254)
    last_name       = models.CharField(max_length=254)
    address         = models.CharField(max_length=254)
    search_group    = models.ForeignKey(SearchGroup)
    
class PersonResult(models.Model):
    first_name      = models.CharField(max_length=254)
    last_name       = models.CharField(max_length=254)
    phone           = models.CharField(max_length=254)
    search_group    = models.ForeignKey(SearchGroup)
    search_attempt  = models.ForeignKey(SearchAttempt)
