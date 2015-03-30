__author__ = 'Kalmar'
from hashlib import md5
from tempfile import TemporaryFile
from datetime import datetime
from django.core.files import File
from hunter import Hunter
from django.core.exceptions import ObjectDoesNotExist
from libhunter.models import Library, Address, Function
from django.contrib.sessions.models import SessionStore
from zipfile import ZipFile


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


def add_library_from_file(library_file, lib_type):
    library_file.seek(0)
    try:
        hunt = Hunter(library_file)
    except Exception as exception:
        raise LibraryProblem("File is corrupted")

    md = md5()
    library_file.seek(0)
    for chunk in chunks(library_file, chunk_size=128):
        md.update(chunk)

    hashsum = md.hexdigest()

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
    functions_in_database = {func.name: func for func in lib_type.function_set.all()}

    function_names_and_addresses = hunt.get_all_non_null_symbols()
    function_names_and_addresses.append(["return", hunt.find_main_return_address()])

    for function, address in function_names_and_addresses:     #  TODO: more flexible solution to missing elements in library
        if function in functions_in_database.keys():
                Address(value=address, library=library, function=functions_in_database[function]).save()
                successful += 1

    if (successful * 1.0 / len(functions_in_database)) < 0.01:
        library.delete()
        raise LibraryProblem('Too few functions present in library')

    return library.id


def add_libraries_from_zip(session_key, zip_bytes, lib_type):
    session = SessionStore(session_key=session_key)
    session['UpdateInfo'] = {"progress": 0, "text": "Starting..."}
    session['Updating'] = True

    tmp_zip = TemporaryFile()
    tmp_zip.write(zip_bytes)
    tmp_zip.seek(0)

    zip_file = ZipFile(tmp_zip)
    namelist = zip_file.namelist()

    done = 0
    errors = 0
    length = len(namelist)

    for name in namelist:
        try:
            tmp_file = TemporaryFile()
            tmp_file.write(zip_file.open(name).read())
            add_library_from_file(File(tmp_file), lib_type)
        except LibraryProblem:
            errors += 1
            pass
        finally:
            done += 1
            session['UpdateInfo'] = {"progress": int(100.0 * done / length), "text": "{}/{} processed ({} errors)".format(done, length, errors)}
            session.save()

    session['UpdateInfo'] = {"progress": 100, "text": "Finished {}/{} where added.".format(length-errors, length)}
    session['Updating'] = False
    session.save()
    return


def add_functions_from_file(session_key, library_bytes, lib_type):
    session = SessionStore(session_key=session_key)
    session['UpdateInfo'] = {"progress": 0, "text": "Starting..."}
    session['Updating'] = True
    session.save()
    library_file = TemporaryFile()
    library_file.write(library_bytes)
    library_file.seek(0)

    try:
        hunt = Hunter(library_file)
    except Exception as exception:
        session['UpdateInfo'] = "File corrupted"
        session.save()
        return

    symbols = hunt.get_all_non_null_symbols()
    symbols.append(["return", hunt.find_main_return_address()])
    successful = 0
    function_names = []
    for function in Function.objects.filter(library=lib_type):
        function_names.append(function.name)
    for name, address in symbols:
        if name not in function_names:
            if Function(name=name, library=lib_type).save() != -1:
                successful += 1
                session['UpdateInfo'] = {"progress": int(100.0*successful/len(symbols)), "text": "{}/{} symbols retrieved".format(successful, len(symbols))}
                session.save()
    session['UpdateInfo'] = {"progress": 100, "text": "Finished"}
    session['Updating'] = False
    session.save()
    return