from django.contrib import admin

from nextcloud_integration.models import NCFolder, NCFile


admin.site.register(NCFolder)
admin.site.register(NCFile)
