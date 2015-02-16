from django.contrib import admin
from hunter import Hunter, FunctionNotFound
from django.core.exceptions import ObjectDoesNotExist
from libhunter.models import LibraryType, Library, Function, Address

# Register your models here.


class FunctionInline(admin.TabularInline):
    model = Function
    fieldsets = [
        (None, {'fields': ['name']})
    ]
    extra = 2


class LibraryInline(admin.StackedInline):
    model = Library
    extra = 0
    fieldsets = [
        (None, {'fields': []}),
    ]


class LibraryTypeAdmin(admin.ModelAdmin):
    inlines = [LibraryInline, FunctionInline]

admin.site.register(LibraryType, LibraryTypeAdmin)

#  TODO: add some documentation (GLOBAL)