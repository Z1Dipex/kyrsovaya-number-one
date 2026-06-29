from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import DatasetOtchet, PracType, DocTemplate, Group, Module, Specialization
from docxtpl import DocxTemplate
import os
import tempfile
import time
from datetime import datetime

def register(request):
    if request.method == "GET":
        return render(request, "register.html", {"form": UserCreationForm()})
    else:
        if request.POST['password1'] == request.POST['password2']:
            user = User.objects.create_user(
                request.POST['username'],
                password=request.POST['password1']
            )
            user.save()
            DatasetOtchet.objects.create(user=user)
            login(request, user)
            return redirect('/profile/')
        else:
            messages.error(request, 'Пароли не совпадают')
            return render(request, "register.html", {"form": UserCreationForm()})

def loginf(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'Вы вошли как {username}')
                return redirect('/profile/')
            else:
                messages.error(request, 'Неправильное имя пользователя или пароль')
        else:
            messages.error(request, 'Неправильное имя пользователя или пароль')

    form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

@login_required
def profile(request):
    user_report, created = DatasetOtchet.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        if 'generate_title' in request.POST:
            return generate_title_document(request, user_report)
        if 'generate_diary' in request.POST:
            return generate_diary_document(request, user_report)
        if 'generate_task' in request.POST:
            return generate_task_document(request, user_report)

        # Сохраняем текстовые поля
        user_report.familia = request.POST.get('familia', '').strip() or None
        user_report.name = request.POST.get('name', '').strip() or None
        user_report.otchestvo = request.POST.get('otchestvo', '').strip() or None
        
        # Сохраняем тип практики
        tip_value = request.POST.get('tip', '')
        if tip_value:
            try:
                user_report.prac_type = PracType.objects.get(type_name=tip_value)
            except PracType.DoesNotExist:
                pass
        else:
            user_report.prac_type = None
        
        # Сохраняем модуль
        module_value = request.POST.get('module', '')
        if module_value:
            try:
                module_obj, created = Module.objects.get_or_create(module_name=module_value)
                user_report.module = module_obj
            except Exception:
                user_report.module = None
        else:
            user_report.module = None
        
        # Сохраняем специальность
        spec_value = request.POST.get('specialization', '')
        if spec_value:
            try:
                spec_obj, created = Specialization.objects.get_or_create(full_spec=spec_value)
                user_report.specialization = spec_obj
            except Exception:
                user_report.specialization = None
        else:
            user_report.specialization = None
        
        # Сохраняем группу
        group_value = request.POST.get('group', '')
        if group_value:
            try:
                group_obj, created = Group.objects.get_or_create(group_name=group_value)
                user_report.group = group_obj
            except Exception:
                user_report.group = None
        else:
            user_report.group = None
        
        # Сохраняем курс
        kurs_value = request.POST.get('kurs', '')
        user_report.kurs = kurs_value if kurs_value else None
        
        # Даты
        begin_date = request.POST.get('begin_date', '')
        if begin_date:
            date_parts = begin_date.split('-')
            if len(date_parts) == 3:
                user_report.date_begin = f"{date_parts[2]}.{date_parts[1]}.{date_parts[0]}"
            else:
                user_report.date_begin = None
        else:
            user_report.date_begin = None
        
        finish_date = request.POST.get('finish_date', '')
        if finish_date:
            date_parts = finish_date.split('-')
            if len(date_parts) == 3:
                user_report.date_finish = f"{date_parts[2]}.{date_parts[1]}.{date_parts[0]}"
            else:
                user_report.date_finish = None
        else:
            user_report.date_finish = None
        
        user_report.head1 = request.POST.get('head1', '').strip() or None
        user_report.head2 = request.POST.get('head2', '').strip() or None
        user_report.ruc_pract = request.POST.get('ruc_pract', '').strip() or None
        
        year_value = request.POST.get('year', '')
        user_report.year = int(year_value) if year_value and year_value.isdigit() else None
        
        hours_value = request.POST.get('hours', '')
        user_report.hours = int(hours_value) if hours_value and hours_value.isdigit() else None
        
        user_report.mdk1 = request.POST.get('mdk1', '').strip() or None
        user_report.mdk2 = request.POST.get('mdk2', '').strip() or None
        user_report.mdk3 = request.POST.get('mdk3', '').strip() or None
        user_report.mdk4 = request.POST.get('mdk4', '').strip() or None

        user_report.save()
        messages.success(request, 'Данные сохранены!')
        return redirect('/profile/')

    # Форматирование дат для input type="date"
    begin_date_for_input = ''
    finish_date_for_input = ''

    if user_report.date_begin:
        try:
            parts = user_report.date_begin.split('.')
            if len(parts) == 3:
                begin_date_for_input = f"{parts[2]}-{parts[1]}-{parts[0]}"
        except:
            pass

    if user_report.date_finish:
        try:
            parts = user_report.date_finish.split('.')
            if len(parts) == 3:
                finish_date_for_input = f"{parts[2]}-{parts[1]}-{parts[0]}"
        except:
            pass

    # Получаем все возможные значения для выпадающих списков
    prac_types = PracType.objects.all()
    groups = Group.objects.all()
    modules = Module.objects.all()
    specializations = Specialization.objects.all()

    has_title_template = DocTemplate.objects.filter(template_type='title', is_active=True).exists()
    has_diary_template = DocTemplate.objects.filter(template_type='diary', is_active=True).exists()
    has_task_template = DocTemplate.objects.filter(template_type='task', is_active=True).exists()

    return render(request, "profile.html", {
        "user_report": user_report,
        "prac_types": prac_types,
        "groups": groups,
        "modules": modules,
        "specializations": specializations,
        "begin_date_for_input": begin_date_for_input,
        "finish_date_for_input": finish_date_for_input,
        "has_title_template": has_title_template,
        "has_diary_template": has_diary_template,
        "has_task_template": has_task_template,
    })

def decline_fio_genitive(familia, name, otchestvo):
    def decline_familia(f):
        if not f:
            return ''
        if f.endswith('а'):
            return f[:-1] + 'ой'
        if f.endswith('я'):
            return f[:-1] + 'ой'
        if f.endswith('ва'):
            return f[:-2] + 'вой'
        if f.endswith('на'):
            return f[:-2] + 'ной'
        if f.endswith('ий'):
            return f[:-2] + 'его'
        if f.endswith('ый'):
            return f[:-2] + 'ого'
        if f.endswith('ой'):
            return f[:-2] + 'ого'
        if f.endswith('ь'):
            return f[:-1] + 'я'
        if f[-1] in 'бвгджзйклмнпрстфхцчшщ':
            return f + 'а'
        return f
    
    def decline_name(n):
        if not n:
            return ''
        if n.endswith('а'):
            return n[:-1] + 'ы'
        if n.endswith('я'):
            return n[:-1] + 'и'
        if n.endswith('й'):
            return n[:-1] + 'я'
        if n.endswith('ь'):
            return n[:-1] + 'я'
        if n[-1] in 'бвгджзйклмнпрстфхцчшщ':
            return n + 'а'
        return n
    
    def decline_otchestvo(o):
        if not o:
            return ''
        if o.endswith('на'):
            return o[:-2] + 'ны'
        if o.endswith('вна'):
            return o[:-3] + 'вны'
        if o.endswith('чна'):
            return o[:-3] + 'чны'
        if o.endswith('ч'):
            return o + 'а'
        if o.endswith('й'):
            return o[:-1] + 'я'
        if o.endswith('а'):
            return o[:-1] + 'ы'
        return o + 'а'
    
    fam = decline_familia(familia)
    nam = decline_name(name)
    otch = decline_otchestvo(otchestvo)
    
    result_parts = []
    if fam:
        result_parts.append(fam)
    if nam:
        result_parts.append(nam)
    if otch:
        result_parts.append(otch)
    return ' '.join(result_parts)

def decline_fio_dative(familia, name, otchestvo):
    def decline_familia(f):
        if not f:
            return ''
        if f.endswith('а'):
            return f[:-1] + 'ой'
        if f.endswith('я'):
            return f[:-1] + 'ой'
        if f.endswith('ва'):
            return f[:-2] + 'вой'
        if f.endswith('на'):
            return f[:-2] + 'ной'
        if f.endswith('ий'):
            return f[:-2] + 'ему'
        if f.endswith('ый'):
            return f[:-2] + 'ому'
        if f.endswith('ой'):
            return f[:-2] + 'ому'
        if f.endswith('ь'):
            return f[:-1] + 'ю'
        if f[-1] in 'бвгджзйклмнпрстфхцчшщ':
            return f + 'у'
        return f
    
    def decline_name(n):
        if not n:
            return ''
        if n.endswith('а'):
            return n[:-1] + 'е'
        if n.endswith('я'):
            return n[:-1] + 'е'
        if n.endswith('й'):
            return n[:-1] + 'ю'
        if n.endswith('ь'):
            return n[:-1] + 'ю'
        if n[-1] in 'бвгджзйклмнпрстфхцчшщ':
            return n + 'у'
        return n
    
    def decline_otchestvo(o):
        if not o:
            return ''
        if o.endswith('на'):
            return o[:-2] + 'не'
        if o.endswith('вна'):
            return o[:-3] + 'вне'
        if o.endswith('чна'):
            return o[:-3] + 'чне'
        if o.endswith('ч'):
            return o + 'у'
        if o.endswith('й'):
            return o[:-1] + 'ю'
        if o.endswith('а'):
            return o[:-1] + 'е'
        return o + 'у'
    
    fam = decline_familia(familia)
    nam = decline_name(name)
    otch = decline_otchestvo(otchestvo)
    
    result_parts = []
    if fam:
        result_parts.append(fam)
    if nam:
        result_parts.append(nam)
    if otch:
        result_parts.append(otch)
    return ' '.join(result_parts)

def format_date_for_title(date_str):
    if not date_str:
        return ''
    try:
        parts = date_str.split('.')
        if len(parts) != 3:
            return date_str
        day = str(int(parts[0]))
        month_num = parts[1]
        year = parts[2]
        months = {
            '01': 'января', '02': 'февраля', '03': 'марта', '04': 'апреля',
            '05': 'мая', '06': 'июня', '07': 'июля', '08': 'августа',
            '09': 'сентября', '10': 'октября', '11': 'ноября', '12': 'декабря'
        }
        month_name = months.get(month_num, month_num)
        return f'"{day}" {month_name} {year}'
    except Exception:
        return date_str

def generate_title_document(request, user_report):
    temp_file_path = None
    try:
        template = DocTemplate.objects.get(template_type='title', is_active=True)

        if user_report.prac_type and user_report.prac_type.type_name == 'Учебная':
            practice_type = "УЧЕБНОЙ"
        else:
            practice_type = "ПРОИЗВОДСТВЕННОЙ"

        fio_genitive = decline_fio_genitive(
            user_report.familia or '',
            user_report.name or '',
            user_report.otchestvo or ''
        )

        date_begin_formatted = format_date_for_title(user_report.date_begin or '')
        date_finish_formatted = format_date_for_title(user_report.date_finish or '')

        # Получаем названия из связанных объектов
        module_name = user_report.module.module_name if user_report.module else ''
        spec_name = user_report.specialization.full_spec if user_report.specialization else ''
        group_name = user_report.group.group_name if user_report.group else ''

        def underline_if_empty(value, length=8):
            if not value or value.strip() == '':
                return '_' * length
            return value

        context = {
            'tip': practice_type,
            'familia': user_report.familia or '',
            'name': user_report.name or '',
            'otchestvo': user_report.otchestvo or '',
            'fio': fio_genitive,
            'module': underline_if_empty(module_name, 8),
            'specialization': underline_if_empty(spec_name, 8),
            'kurs': user_report.kurs or '',
            'group': underline_if_empty(group_name, 8),
            'date_begin': date_begin_formatted,
            'date_finish': date_finish_formatted,
            'head1': underline_if_empty(user_report.head1, 8),
            'head2': underline_if_empty(user_report.head2, 8),
            'ruc_pract': underline_if_empty(user_report.ruc_pract, 8),
            'year': user_report.year or datetime.now().year,
        }

        doc = DocxTemplate(template.file.path)
        doc.render(context)

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        temp_file_path = temp_file.name
        temp_file.close()

        doc.save(temp_file_path)
        time.sleep(0.1)

        with open(temp_file_path, 'rb') as f:
            file_content = f.read()

        try:
            os.remove(temp_file_path)
        except:
            pass

        filename = f"{user_report.familia}_{user_report.name}_Титульный_лист_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

        response = HttpResponse(file_content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        messages.success(request, 'Титульный лист успешно сгенерирован!')
        return response

    except DocTemplate.DoesNotExist:
        messages.error(request, 'Шаблон титульного листа не найден')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass

    return redirect('/profile/')

def generate_diary_document(request, user_report):
    temp_file_path = None
    try:
        template = DocTemplate.objects.get(template_type='diary', is_active=True)

        full_fio = f"{user_report.familia or ''} {user_report.name or ''} {user_report.otchestvo or ''}".strip()
        fio_genitive = decline_fio_genitive(
            user_report.familia or '',
            user_report.name or '',
            user_report.otchestvo or ''
        )

        # Определяем тип практики (ВСЕ БУКВЫ ЗАГЛАВНЫЕ)
        if user_report.prac_type and user_report.prac_type.type_name == 'Учебная':
            practice_type = "УЧЕБНОЙ"
        else:
            practice_type = "ПРОИЗВОДСТВЕННОЙ"

        # Получаем названия из связанных объектов
        module_name = user_report.module.module_name if user_report.module else ''
        spec_name = user_report.specialization.full_spec if user_report.specialization else ''
        group_name = user_report.group.group_name if user_report.group else ''

        # Функция для извлечения только кода модуля (ПМ.08, ПМд.13 и т.д.)
        def extract_module_code(module_full_name):
            if not module_full_name:
                return ''
            
            # Ищем паттерн ПМ.xx или ПМд.xx или ПМ.xx с пробелом
            import re
            # Паттерн ищет: ПМ (возможно с маленькой буквой д) и затем цифры через точку
            # НЕ используем .upper() чтобы сохранить оригинальный регистр
            match = re.search(r'ПМ[д]?\.[0-9]+', module_full_name, re.IGNORECASE)
            if match:
                return match.group(0)  # УБИРАЕМ .upper()
            
            # Если не нашли, берем первые 6 символов
            return module_full_name[:6] if len(module_full_name) > 6 else module_full_name

        module_short = extract_module_code(module_name)

        def underline_if_empty(value, length=8):
            if value is None:
                return '_' * length
            value_str = str(value).strip()
            if not value_str:
                return '_' * length
            return value_str

        kurs_str = str(user_report.kurs) if user_report.kurs else ''
        hours_str = str(user_report.hours) if user_report.hours else ''

        context = {
            'tip': practice_type,
            'familia': user_report.familia or '',
            'name': user_report.name or '',
            'otchestvo': user_report.otchestvo or '',
            'fio': fio_genitive,
            'fio_nominative': full_fio,
            'group': group_name,
            'kurs': kurs_str,
            'specialization': underline_if_empty(spec_name, 5),
            'module': module_short,
            'module_full': underline_if_empty(module_name, 5),
            'mdk1': underline_if_empty(user_report.mdk1, 30),
            'mdk2': underline_if_empty(user_report.mdk2, 30),
            'mdk3': underline_if_empty(user_report.mdk3, 30),
            'mdk4': underline_if_empty(user_report.mdk4, 30),
            'head1': underline_if_empty(user_report.head1, 40),
            'head2': underline_if_empty(user_report.head2, 8),
            'ruc_pract': underline_if_empty(user_report.ruc_pract, 8),
            'hours': hours_str,
            'year': user_report.year or datetime.now().year,
        }

        doc = DocxTemplate(template.file.path)
        doc.render(context)

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        temp_file_path = temp_file.name
        temp_file.close()

        doc.save(temp_file_path)
        time.sleep(0.1)

        with open(temp_file_path, 'rb') as f:
            file_content = f.read()

        try:
            os.remove(temp_file_path)
        except:
            pass

        filename = f"{user_report.familia}_{user_report.name}_Дневник_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

        response = HttpResponse(file_content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        messages.success(request, 'Дневник успешно сгенерирован!')
        return response

    except DocTemplate.DoesNotExist:
        messages.error(request, 'Шаблон дневника не найден')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass

    return redirect('/profile/')

def generate_task_document(request, user_report):
    temp_file_path = None
    try:
        template = DocTemplate.objects.get(template_type='task', is_active=True)

        if user_report.prac_type and user_report.prac_type.type_name == 'Учебная':
            practice_type = "учебной"
            practice_type_short = "учебную"
        else:
            practice_type = "производственной"
            practice_type_short = "производственную"

        full_fio = f"{user_report.familia or ''} {user_report.name or ''} {user_report.otchestvo or ''}".strip()
        fio_dative = decline_fio_dative(
            user_report.familia or '',
            user_report.name or '',
            user_report.otchestvo or ''
        )

        date_begin_normal = user_report.date_begin or ''
        date_finish_normal = user_report.date_finish or ''

        # Получаем названия из связанных объектов
        module_name = user_report.module.module_name if user_report.module else ''
        spec_name = user_report.specialization.full_spec if user_report.specialization else ''
        group_name = user_report.group.group_name if user_report.group else ''

        def underline_if_empty(value, length=40):
            # ПРЕОБРАЗУЕМ В СТРОКУ, ЕСЛИ ПРИШЛО ЧИСЛО
            if value is None:
                return '_' * length
            value_str = str(value).strip()
            if not value_str:
                return '_' * length
            return value_str

        # ПРЕОБРАЗУЕМ kurs И hours В СТРОКУ
        kurs_str = str(user_report.kurs) if user_report.kurs else ''
        hours_str = str(user_report.hours) if user_report.hours else ''

        context = {
            'tip': practice_type,
            'tip_short': practice_type_short,
            'familia': user_report.familia or '',
            'name': user_report.name or '',
            'otchestvo': user_report.otchestvo or '',
            'fio': full_fio,
            'fio_dative': fio_dative,
            'group': group_name,
            'kurs': kurs_str,
            'specialization': underline_if_empty(spec_name, 50),
            'module': underline_if_empty(module_name, 50),
            'mdk1': underline_if_empty(user_report.mdk1, 50),
            'mdk2': underline_if_empty(user_report.mdk2, 50),
            'mdk3': underline_if_empty(user_report.mdk3, 50),
            'mdk4': underline_if_empty(user_report.mdk4, 50),
            'head1': underline_if_empty(user_report.head1, 40),
            'head2': underline_if_empty(user_report.head2, 40),
            'ruc_pract': underline_if_empty(user_report.ruc_pract, 40),
            'date_begin': date_begin_normal,
            'date_finish': date_finish_normal,
            'hours': hours_str,
            'year': user_report.year or datetime.now().year,
        }

        doc = DocxTemplate(template.file.path)
        doc.render(context)

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        temp_file_path = temp_file.name
        temp_file.close()

        doc.save(temp_file_path)
        time.sleep(0.1)

        with open(temp_file_path, 'rb') as f:
            file_content = f.read()

        try:
            os.remove(temp_file_path)
        except:
            pass

        filename = f"{user_report.familia}_{user_report.name}_Задание_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

        response = HttpResponse(file_content, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        messages.success(request, 'Задание успешно сгенерировано!')
        return response

    except DocTemplate.DoesNotExist:
        messages.error(request, 'Шаблон задания не найден')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass

    return redirect('/profile/')

def logoutf(request):
    logout(request)
    return redirect('/login/')