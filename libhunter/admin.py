from django.contrib import admin
from libhunter.models import LibraryType, Library, Function, Address
# Register your models here.


admin.site.register(LibraryType)
admin.site.register(Library)
admin.site.register(Function)
admin.site.register(Address)

#  TODO: customize admin panel
#  TODO: add file deletion when deleting library in admin panel
#  TODO: add automatic new functions resolving in libraries