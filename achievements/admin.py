from django.contrib import admin
from .models import Category, Achievement, Claimant

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    list_display_links = ('id', 'name')

admin.site.register(Category, CategoryAdmin)

class ClaimantInline(admin.TabularInline):
    model = Claimant
    extra = 0

class AchievementAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'is_public')
    list_filter = ['category', 'is_public']
    list_display_links = ('id', 'name')

    inlines = [ClaimantInline]

admin.site.register(Achievement, AchievementAdmin)

