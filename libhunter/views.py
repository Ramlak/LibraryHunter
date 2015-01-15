from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.core.servers.basehttp import FileWrapper
from libhunter.models import Library, LibraryType, Address
from django.db import IntegrityError
from shutil import make_archive
from django.core.urlresolvers import reverse
from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import NamedTemporaryFile
from libhunter.hunter import *
from hashlib import md5
from os.path import basename
from django.core.exceptions import ObjectDoesNotExist
from libhunter.forms import UploadForm, SearchForm
from datetime import datetime

# Create your views here.


def index(request):
    return render(request, 'libhunter/index.html', {'content': 'libhunter/search.html', 'form': SearchForm})


def add(request):
    return render(request, 'libhunter/index.html', {'content': 'libhunter/add.html', 'form': UploadForm})


def list(request):
    libs = Library.objects.order_by('-add_date')
    return render(request, 'libhunter/index.html', {'libs': libs, 'content': 'libhunter/list.html'})


def download(request, id):
    lib = get_object_or_404(Library, pk=id)
    tmp = NamedTemporaryFile()
    zip = ZipFile(tmp.name, "w")
    zip.write(lib.file.name, basename(lib.file.name), compress_type=ZIP_DEFLATED)
    zip.close()
    response = HttpResponse(FileWrapper(open(tmp.name, "rb")), content_type='application/x-zip-compressed')
    response['Content-Disposition'] = "attachment; filename={}.zip".format(lib.name())
    return response


def download_all(request):
    tmp = NamedTemporaryFile()
    response = HttpResponse(FileWrapper(open(make_archive(tmp.name, 'zip', root_dir='libs'), "rb")), content_type='application/x-zip-compressed')
    response['Content-Disposition'] = "attachment; filename=libraries.zip"
    return response


def add_lib(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data.get('file')
            try:
                hunt = Hunter(file)
            except WrongFile:
                return redirect(reverse('add'))

            md = md5()

            for chunk in file.chunks(chunk_size=128):
                md.update(chunk)

            hashsum = md.hexdigest()
            library_type = form.library_type
            try:
                lib_type = LibraryType.objects.get(name__iexact=library_type)
            except ObjectDoesNotExist:
                return redirect(reverse('add'))

            try:
                Library.objects.get(hashsum=hashsum)
                return redirect(reverse('add'))
            except ObjectDoesNotExist:
                pass


            new_lib_parameters = {}
            new_lib_parameters['bits'] = hunt.get_bits_mode()
            new_lib_parameters['hashsum'] = hashsum
            new_lib_parameters['description'] = hunt.get_description()
            new_lib_parameters['file'] = file
            new_lib_parameters['add_date'] = datetime.now()
            new_lib_parameters['type'] = lib_type

            library = Library(**new_lib_parameters)
            library.save()

            for function in lib_type.function_set.all():
                if function.name.lower() != 'return':
                    try:
                         Address(value=hunt.find_function_address_by_name(function.name.lower()), library=library, function=function).save()
                    except FunctionNotFound:
                        pass  # TODO: what if there is no function in library of library_type and there should be?
                else:
                    try:
                        Address(value=hunt.find_main_return_address(), library=library, function=function).save()
                    except FunctionNotFound:
                        pass  # TODO: what if return address cannot be specified?

            return redirect(reverse('show', args=[library.id]))
        else:
            return redirect(reverse('add'))
    else:
        return redirect(reverse('add'))


def show(request, id):
    library = get_object_or_404(Library, pk=id)
    addresses = library.address_set.filter(function__in=library.type.function_set.all())
    return render(request, 'libhunter/index.html', {'content': 'libhunter/show.html', 'lib': library, 'addresses': addresses})


def result(request):
    try:
        function = request.POST['function']
        address = request.POST['address']
        bits = request.POST['bits']
        library_type = request.POST['library_type']
    except KeyError:
        return render(request, 'libhunter/index.html', {'content': 'libhunter/result.html', 'error_message': 'Some parameters were not set'})

    allowed_bits = ['32', '64']

    if bits not in allowed_bits:
        return render(request, 'libhunter/index.html', {'content': 'libhunter/result.html', 'error_message': 'Invalid bit value'})

    bits = int(bits)

    entropy = 0xfff

    try:
        address = int(address, 16)
    except ValueError:
        return render(request, 'libhunter/index.html', {'content': 'libhunter/result.html', 'error_message': 'Address is not a valid hex number'})

    try:
        libraries = LibraryType.objects.get(name__iexact=library_type).library_set.filter(bits=32)
    except ObjectDoesNotExist:
        return render(request, 'libhunter/index.html', {'content': 'libhunter/result.html', 'error_message': 'No such library type/no libraries'})

    correct_libs = []

    for lib in libraries:
        try:
            if (lib.address_set.get(function__name__iexact=function).value & entropy) == (address & entropy):
                correct_libs.append([lib, lib.address_set.get(function__name__iexact=function).value])
        except ObjectDoesNotExist:
            hunt = Hunter(open(lib.file.name, "rb"))
            try:
                found = hunt.find_function_address_by_name(function)
                if (found & entropy) == (address & entropy):
                    correct_libs.append([lib, found])
            except FunctionNotFound:
                pass

    if len(correct_libs) == 0:
        return render(request, 'libhunter/index.html', {'content': 'libhunter/result.html', 'error_message': 'No matching libraries'})

    return render(request, 'libhunter/index.html', {'content': 'libhunter/result.html', 'resolved': correct_libs, 'name': function.lower()})