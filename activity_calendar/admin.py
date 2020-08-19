from django.contrib import admin
from .models import Activity, ActivitySlot, Participant

admin.site.register([Activity, ActivitySlot, Participant])
