__author__ = 'Kalmar'
from hashlib import md5
from datetime import datetime
from hunter import Hunter, WrongFile, FunctionNotFound
from django.core.exceptions import ObjectDoesNotExist
from libhunter.models import LibraryType, Library, Address


class LibraryProblem(Exception):
    def __init__(self, msg):
        self.message = str(msg)


def chunks(file_object, chunk_size=1024):
    """Lazy function (generator) to read a file piece by piece.
    Default chunk size: 1k."""
    while True:
        data = file_object.read(chunk_size)
        if not data:
            break
        yield data


def add_library_from_file(library_file, library_type):
    library_file.seek(0)

    try:
        hunt = Hunter(library_file)
    except WrongFile:
        raise LibraryProblem("File not correct")

    md = md5()
    library_file.seek(0)
    for chunk in chunks(library_file, chunk_size=128):
        md.update(chunk)

    hashsum = md.hexdigest()
    try:
        lib_type = LibraryType.objects.get(name__iexact=library_type)
    except ObjectDoesNotExist:
        raise LibraryProblem("No such library type")

    try:
        Library.objects.get(hashsum=hashsum)
        raise LibraryProblem("Library already exists")
    except ObjectDoesNotExist:
        pass

    library_file.seek(0)

    new_lib_parameters = {}
    new_lib_parameters['bits'] = hunt.get_bits_mode()
    new_lib_parameters['hashsum'] = hashsum
    new_lib_parameters['description'] = hunt.get_description()
    new_lib_parameters['file'] = library_file
    new_lib_parameters['add_date'] = datetime.now()
    new_lib_parameters['type'] = lib_type

    library = Library(**new_lib_parameters)
    library.save()

    successful = 0

    for function in lib_type.function_set.all():     #  TODO: more flexible solution to missing elements in library
        if function.name.lower() != 'return':
            try:
                Address(value=hunt.find_function_address_by_name(function.name.lower()), library=library, function=function).save()
                successful += 1
            except FunctionNotFound:
                pass
        else:
            try:
                Address(value=hunt.find_main_return_address(), library=library, function=function).save()
                successful += 1
            except FunctionNotFound:
                pass

        if successful * 1.0 / len(lib_type.function_set.all()) < 0.2:
            library.delete()
            raise LibraryProblem('Too few functions present in library')

    return library.id
