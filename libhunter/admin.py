from django.contrib import admin
from hunter import Hunter, FunctionNotFound
from django.core.exceptions import ObjectDoesNotExist
from libhunter.models import LibraryType, Library, Function, Address

# Register your models here.


class FunctionAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        libraries = Library.objects.filter(type=obj.library)
        try:
            obj.library.function_set.get(name__iexact=obj.name)
            return
        except ObjectDoesNotExist:
            pass

        obj.save()
        found = 0

        for lib in libraries:
            hunt = Hunter(lib.file)
            if obj.name.lower() == "return":
                try:
                    return_address = hunt.find_main_return_address()
                    Address(library=lib, function=obj, value=return_address).save()
                    found += 1
                except FunctionNotFound:
                    pass
            else:
                try:
                    function_address = hunt.find_function_address_by_name(obj.name)
                    Address(library=lib, function=obj, value=function_address).save()
                    found += 1
                except FunctionNotFound:
                    pass

        if found == 0:
            obj.delete()

admin.site.register(LibraryType)
admin.site.register(Library)
admin.site.register(Function, FunctionAdmin)
admin.site.register(Address)

#  TODO: customize admin panel
#  TODO: add file deletion when deleting library in admin panel