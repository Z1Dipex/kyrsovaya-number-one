from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    name = models.TextField()

    class Meta:
        managed = False
        db_table = 'document'
    
    def __str__(self):
        return self.name


class PracType(models.Model):
    id_prac_type = models.AutoField(primary_key=True)
    type_name = models.TextField(unique=True)

    class Meta:
        managed = False
        db_table = 'prac_type'
    
    def __str__(self):
        return self.type_name


class Group(models.Model):
    id_group = models.AutoField(primary_key=True)
    group_name = models.TextField(unique=True)

    class Meta:
        managed = False
        db_table = 'groups'
    
    def __str__(self):
        return self.group_name


class Module(models.Model):
    id_module = models.AutoField(primary_key=True)
    module_name = models.TextField(unique=True)

    class Meta:
        managed = False
        db_table = 'modules'
    
    def __str__(self):
        return self.module_name


class Specialization(models.Model):
    id_spec = models.AutoField(primary_key=True)
    full_spec = models.TextField(unique=True)

    class Meta:
        managed = False
        db_table = 'specializations'
    
    def __str__(self):
        return self.full_spec


class DatasetOtchet(models.Model):
    id_dataset = models.AutoField(primary_key=True)
    familia = models.TextField(blank=True, null=True)
    name = models.TextField(blank=True, null=True)
    otchestvo = models.TextField(blank=True, null=True)
    
    # Внешние ключи
    prac_type = models.ForeignKey(
        PracType, 
        on_delete=models.SET_NULL, 
        db_column='prac_type_id', 
        null=True, 
        blank=True
    )
    module = models.ForeignKey(
        Module, 
        on_delete=models.SET_NULL, 
        db_column='module_id', 
        null=True, 
        blank=True
    )
    specialization = models.ForeignKey(
        Specialization, 
        on_delete=models.SET_NULL, 
        db_column='spec_id', 
        null=True, 
        blank=True
    )
    group = models.ForeignKey(
        Group, 
        on_delete=models.SET_NULL, 
        db_column='group_id', 
        null=True, 
        blank=True
    )
    
    kurs = models.TextField(blank=True, null=True)
    date_begin = models.TextField(blank=True, null=True)
    date_finish = models.TextField(blank=True, null=True)
    head1 = models.TextField(blank=True, null=True)
    head2 = models.TextField(blank=True, null=True)
    ruc_pract = models.TextField(blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        db_column='user_id', 
        null=True, 
        blank=True
    )
    hours = models.IntegerField(blank=True, null=True, verbose_name='Количество часов')
    mdk1 = models.TextField(blank=True, null=True, verbose_name='МДК 01.01')
    mdk2 = models.TextField(blank=True, null=True, verbose_name='МДК 01.02')
    mdk3 = models.TextField(blank=True, null=True, verbose_name='МДК 01.03')
    mdk4 = models.TextField(blank=True, null=True, verbose_name='МДК 01.04')

    class Meta:
        managed = False
        db_table = 'dataset_otchet'
    
    def __str__(self):
        return f"{self.familia} {self.name} {self.otchestvo} - {self.group.group_name if self.group else ''}"


class DocTemplate(models.Model):
    TEMPLATE_TYPES = [
        ('title', 'Титульный лист'),
        ('diary', 'Дневник отчета'),
        ('task', 'Задание на практику'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Название шаблона')
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES, verbose_name='Тип шаблона')
    file = models.FileField(upload_to='templates/', verbose_name='Файл шаблона')
    description = models.TextField(blank=True, verbose_name='Описание')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    class Meta:
        managed = True
        db_table = 'doc_template'
        verbose_name = 'Шаблон документа'
        verbose_name_plural = 'Шаблоны документов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"