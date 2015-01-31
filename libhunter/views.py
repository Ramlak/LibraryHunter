from shutil import make_archive
from zipfile import ZipFile, ZIP_DEFLATED, is_zipfile
from tempfile import NamedTemporaryFile
from functions import  add_library_from_file, LibraryProblem
from os.path import basename
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages

from libhunter.models import Library, LibraryType
from libhunter.hunter import *
from libhunter.forms import UploadForm, SearchForm


# Create your views here.


def index(request):
    return render(request, 'libhunter/index.html', {'content': 'libhunter/search.html', 'form': SearchForm})


def add(request):
    return render(request, 'libhunter/index.html', {'content': 'libhunter/add.html', 'form': UploadForm, 'note':
    'Now supports zip upload!'})


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
    response = HttpResponse(FileWrapper(open(make_archive(tmp.name, 'zip', root_dir='libs'), "rb")),
                            content_type='application/x-zip-compressed')
    response['Content-Disposition'] = "attachment; filename=libraries.zip"
    return response


def info(request):
    return render(request, 'libhunter/index.html', {'content': 'libhunter/info.html'})


def add_lib(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():

            file = form.cleaned_data['file']
            library_type = form.cleaned_data['library_type']

            if not is_zipfile(file):
                try:
                    added_id = add_library_from_file(file, library_type)
                    return redirect(reverse('show', args=[added_id]))
                except LibraryProblem as exception:
                    messages.add_message(request, messages.ERROR, exception.message)
                    return redirect(reverse('info'))
            else:
                zip = ZipFile(file, 'r')
                successful = 0
                for name in zip.namelist():
                    try:
                        added_id = add_library_from_file(zip.open(name, 'rb'), library_type)
                        successful += 1
                    except LibraryProblem as exception:
                        pass
                messages.add_message(request, messages.ERROR, '{}/{} libraries uploaded correctly'.format(successful, len(zip.namelist())))
                return redirect(reverse('info'))
        else:
            return redirect(reverse('add'))
    else:
        return redirect(reverse('add'))


def show(request, id):
    library = get_object_or_404(Library, pk=id)
    addresses = library.address_set.filter(function__in=library.type.function_set.all())
    return render(request, 'libhunter/index.html',
                  {'content': 'libhunter/show.html', 'lib': library, 'addresses': addresses})


def result(request):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():

            function = form.cleaned_data['function']
            address = form.cleaned_data['address']
            bits = form.cleaned_data['bits']
            library_type = form.cleaned_data['library_type']

            allowed_bits = ['32', '64']

            if bits not in allowed_bits:
                messages.add_message(request, messages.ERROR, 'Invalid bit value')
                return redirect(reverse('info'))

            bits = int(bits)
            entropy = 0xfff

            try:
                address = int(address, 16)
            except ValueError:
                messages.add_message(request, messages.ERROR, 'Address is not a valid hex number')
                return redirect(reverse('info'))

            try:
                libraries = LibraryType.objects.get(name__iexact=library_type).library_set.filter(bits=bits)
            except ObjectDoesNotExist:
                messages.add_message(request, messages.ERROR, 'No such library type/no libraries')
                return redirect(reverse('info'))

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
                messages.add_message(request, messages.ERROR, 'No matching libraries')
                return redirect(reverse('info'))

            return render(request, 'libhunter/index.html',
                          {'content': 'libhunter/result.html', 'resolved': correct_libs, 'name': function.lower()})
        else:
            messages.add_message(request, messages.ERROR, 'Form fields are corrupted.')
            return redirect(reverse('info'))
    else:
        messages.add_message(render, messages.ERROR, 'Must be POST method!')
        return redirect(reverse('info'))