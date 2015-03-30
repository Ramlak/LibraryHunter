import json
import urllib2
from shutil import make_archive, copyfileobj
from zipfile import ZipFile, ZIP_DEFLATED, is_zipfile
from tempfile import NamedTemporaryFile
from functions import add_library_from_file, LibraryProblem, add_functions_from_file, add_libraries_from_zip
from os.path import basename
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.core.files import File
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from libhunter.models import Library, LibraryType
from libhunter.hunter import *
from libhunter.forms import UploadForm, SearchForm
from django.contrib.auth.decorators import login_required
from threading import Thread

# Create your views here.


def index(request):
    return render(request, 'libhunter/search.html', {'form': SearchForm})


def add(request):
    return render(request, 'libhunter/add.html', {'form': UploadForm, 'note':
    'Now supports zip upload!'})


def list(request):
    libs = Library.objects.order_by('-add_date')
    return render(request, 'libhunter/list.html', {'libs': libs})


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
    return render(request, 'libhunter/info.html', {})


def add_lib(request):
    if request.method == 'POST':
        request.session['Updating'] = False
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data['file']:
                file = form.cleaned_data['file']
            elif form.cleaned_data['url']:
                url = form.cleaned_data['url']
                file = NamedTemporaryFile()
                file.write(urllib2.urlopen(url).read())
                file = File(file)
                file.seek(0)
            else:
                messages.add_message(request, messages.ERROR, "You must provide file or url!")
                return redirect(reverse('info'))

            library_type_id = form.cleaned_data['library_type']
            try:
                library_id = LibraryType.objects.get(id=library_type_id)
            except ObjectDoesNotExist:
                messages.add_message(request, messages.ERROR, "Wrong LibraryType")
                return redirect(reverse('info'))

            if not is_zipfile(file):
                try:
                    added_id = add_library_from_file(file, library_id)
                    return redirect(reverse('show', args=[added_id]))
                except LibraryProblem as exception:
                    messages.add_message(request, messages.ERROR, exception.message)
                    return redirect(reverse('info'))
            else:
                file.seek(0)
                zip_bytes = file.read()
                Thread(target=add_libraries_from_zip, args=(request.session.session_key, zip_bytes, library_id)).start()
                request.session['Updating'] = True
                return redirect(reverse('info'))
        else:
            messages.add_message(request, messages.ERROR, 'Form is invalid.')
            return redirect(reverse('info'))
    else:
        messages.add_message(request, messages.ERROR, 'Only POST method is allowed.')
        return redirect(reverse('info'))


def show(request, id):
    library = get_object_or_404(Library, pk=id)
    addresses = library.address_set.filter(function__in=library.type.function_set.all())
    return render(request, 'libhunter/show.html',
                  {'lib': library, 'addresses': addresses})


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

            return render(request, 'libhunter/result.html',
                          {'resolved': correct_libs, 'name': function.lower()})
        else:
            messages.add_message(request, messages.ERROR, 'Form fields are corrupted.')
            return redirect(reverse('info'))
    else:
        messages.add_message(render, messages.ERROR, 'Must be POST method!')
        return redirect(reverse('info'))


def update_status(request):
    object = request.session['UpdateInfo']
    data = json.dumps(object)
    return HttpResponse(data)

@login_required()
def update(request):
    return render(request, 'libhunter/update.html', {'form': UploadForm})


@login_required()
def update_functions(request):
    if request.method != 'POST':
        messages.add_message(request, messages.ERROR, 'Only POST method is allowed.')
        return redirect(reverse('info'))
    form = UploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.add_message(request, messages.ERROR, 'Form is invalid.')
        return redirect(reverse('info'))
    file = form.cleaned_data['file'].read()
    library_type_id = form.cleaned_data['library_type']
    try:
        library_type = LibraryType.objects.get(id=library_type_id)
        Thread(target=add_functions_from_file, args=(request.session.session_key, file, library_type)).start()
    except ObjectDoesNotExist:
        messages.add_message(request, messages.ERROR, "No such library type.")
        request.session['Updating'] = False
        return redirect(reverse('info'))
    request.session['Updating'] = True
    return redirect(reverse('info'))