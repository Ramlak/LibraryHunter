# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import libhunter.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('value', models.IntegerField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Function',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Library',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=200)),
                ('bits', models.IntegerField()),
                ('add_date', models.DateTimeField(verbose_name=b'date added')),
                ('file', models.FileField(upload_to=libhunter.models.upload_filename)),
                ('hashsum', models.CharField(unique=True, max_length=32)),
            ],
            options={
                'verbose_name_plural': 'Libraries',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LibraryType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=40, verbose_name=b'Type')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='library',
            name='type',
            field=models.ForeignKey(to='libhunter.LibraryType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='function',
            name='library',
            field=models.ForeignKey(verbose_name=b'Library type', to='libhunter.LibraryType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='address',
            name='function',
            field=models.ForeignKey(to='libhunter.Function'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='address',
            name='library',
            field=models.ForeignKey(to='libhunter.Library'),
            preserve_default=True,
        ),
    ]
