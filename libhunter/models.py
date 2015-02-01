from django.db import models
from os import path
from django.dispatch import receiver
from shutil import move
from datetime import datetime

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

    def name(self):
        return path.basename(str(self.file))

    def __str__(self):
        return "{}\t\t\t{} bit".format(self.description, self.bits)


class Function(models.Model):
    name = models.CharField(max_length=50)
    library = models.ForeignKey(LibraryType, verbose_name="Library type")

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