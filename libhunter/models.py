from django.db import models
from os import path
from django.dispatch import receiver
from shutil import move
from datetime import datetime
from hunter import Hunter, FunctionNotFound
from django.core.exceptions import ObjectDoesNotExist

# Create your models here.


def upload_filename(instance, filename):
    return path.join('libs/', instance.type.name.lower() + "_" + instance.hashsum)


class LibraryType(models.Model):
    name = models.CharField(verbose_name="Type", max_length=40, unique=True)

    def __str__(self):
        return str(self.name)


class Library(models.Model):
    description = models.CharField(max_length=200)
    bits = models.IntegerField()
    add_date = models.DateTimeField('date added')
    file = models.FileField(upload_to=upload_filename)
    hashsum = models.CharField(max_length=32, unique=True)
    type = models.ForeignKey(LibraryType)

    class Meta:
        verbose_name_plural = 'Libraries'

    def name(self):
        return path.basename(str(self.file))

    def __str__(self):
        return "{}\t\t\t{} bit".format(self.description, self.bits)


class Function(models.Model):
    name = models.CharField(max_length=50)
    library = models.ForeignKey(LibraryType, verbose_name="Library type")

    def save(self, *args):
        libraries = Library.objects.filter(type=self.library)
        if len(libraries) == 0:
            super(Function, self).save()
            return
        try:
            self.library.function_set.get(name__iexact=self.name)
            return -1
        except ObjectDoesNotExist:
            pass

        super(Function, self).save()
        found = 0

        for lib in libraries:
            hunt = Hunter(lib.file)
            if self.name.lower() == "return":
                try:
                    return_address = hunt.find_main_return_address()
                    Address(library=lib, function=self, value=return_address).save()
                    found += 1
                except FunctionNotFound:
                    pass
            else:
                try:
                    function_address = hunt.find_function_address_by_name(self.name)
                    Address(library=lib, function=self, value=function_address).save()
                    found += 1
                except FunctionNotFound:
                    pass

        if found == 0:
            self.delete()
            return -1

    def __str__(self):
        return str(self.name)


class Address(models.Model):
    function = models.ForeignKey(Function)
    library = models.ForeignKey(Library)
    value = models.IntegerField()

    def __str__(self):
        return str(self.function) + "_" + str(self.library.id).lower()


@receiver(models.signals.post_delete, sender=Library)
def auto_move_library_file_to_trash(sender, instance, **kwargs):
    if instance.file:
        if path.isfile(instance.file.path):
            now = datetime.now()
            move(instance.file.path, 'trash/{}_{}-{}-{}_{}-{}'.format(path.basename(instance.file.path), now.year, now.month, now.day, now.hour, now.minute))