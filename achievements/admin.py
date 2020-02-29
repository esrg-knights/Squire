from django.contrib import admin
from .models import Category, Achievement, Claimant

# Register your models here.
admin.site.register(Category)
admin.site.register(Achievement)
admin.site.register(Claimant)
