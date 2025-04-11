from django.shortcuts import render, redirect
from django.http import HttpResponse,Http404
from .models import Mentorados, Navigators,DisponibilidadeHorarios,Reuniao, Tarefa, Upload
from django.contrib import messages
from django.contrib.messages import constants
from datetime import datetime, timedelta
from .auth import valida_token
from django.contrib.auth.decorators import login_required


@login_required
def mentorados(request):
    # O if nao esta errado mas com a importação do 'login_required' e mais eficiente
    # if not request.user.is_authenticated:
        # return redirect('login')
    
    if request.method == 'GET':
        navigators = Navigators.objects.filter(user=request.user)
        mentorados = Mentorados.objects.filter(user=request.user)

        #TODO: uma forma de vazer essa lista é usando (list comprehension) Estudar depois
        #TODO: estagios_flat = [i[1] for i in Mentorados.estagio_choices]

        estagios_flat = []
        for i in Mentorados.estagio_choices:
            estagios_flat.append(i[1])

        qtd_estagios = []
        for i,j in Mentorados.estagio_choices:
            x = Mentorados.objects.filter(estagio=i).filter(user=request.user).count()
            qtd_estagios.append(x)

        return render(request, 'mentorados.html',
        {'estagios': Mentorados.estagio_choices, 'navigators': navigators, 'mentorados': mentorados, 'estagios_flat': estagios_flat, 'qtd_estagios': qtd_estagios})
    elif request.method == 'POST':
        nome = request.POST.get('nome')
        foto = request.FILES.get('foto')
        estagio = request.POST.get("estagio")
        navigator = request.POST.get('navigator')

        mentorado = Mentorados(
            nome=nome,
            foto=foto,
            estagio=estagio,
            navigator_id=navigator,
            user=request.user
        )

        mentorado.save()

        messages.add_message(request, constants.SUCCESS, 'Mentorado cadastrado com sucesso')
        return redirect('mentorados')

@login_required
def reunioes(request):
    if request.method == 'GET':
        reunioes = Reuniao.objects.filter(data__mentor=request.user)
        return render(request, 'reunioes.html', {'reunioes': reunioes})
    elif request.method == 'POST':
        data = request.POST.get('data')
        data = datetime.strptime(data, '%Y-%m-%dT%H:%M')

        disponibilidades = DisponibilidadeHorarios.objects.filter(mentor=request.user).filter(
            data_inicial__gte=(data - timedelta(minutes=50)),
            data_inicial__lte=(data + timedelta(minutes=50))
        )

        if disponibilidades.exists():
            messages.add_message(request, constants.ERROR, 'Você ja possui uma reunião em aberto')
            return redirect('reunioes')

        disponibilidades = DisponibilidadeHorarios(
            data_inicial = data,
            mentor=request.user,
        )
        disponibilidades.save()

        messages.add_message(request, constants.SUCCESS, 'Horario marcado com sucesso')
        return redirect('reunioes')
    
def auth(request):
    if request.method == 'GET':
        print(request.COOKIES)
        return render(request, 'auth_mentorado.html')
    elif request.method == 'POST':
        token = request.POST.get('token')

        if not Mentorados.objects.filter(token=token).exists():
            messages.add_message(request, constants.ERROR, 'Token inválido')
            return redirect('auth_mentorado')
        
        response = redirect('escolher_dia')
        response.set_cookie('auth_token', token, max_age=3600)

        return response
     
def escolher_dia(request):
    if not valida_token(request.COOKIES.get('auth_token')):
        return redirect('auth_mentorado')
    
    if request.method == 'GET':
       mentorado = valida_token(request.COOKIES.get('auth_token'))

       disponibilidades = DisponibilidadeHorarios.objects.filter(
           data_inicial__gte=datetime.now(),
           agendado=False,
           mentor=mentorado.user
       ).values_list('data_inicial', flat=True)

       datas = []
       for i in disponibilidades:
           datas.append(i.date().strftime('%d-%m-%y'))

        #TODO: tornar o mes e o dia da semana dinamicos
       return render(request, 'escolher_dia.html', {'horarios': list(set(datas))})
    
def agendar_reuniao(request):
    if not valida_token(request.COOKIES.get('auth_token')):
        return redirect('auth_mentorado')
    
    mentorado = valida_token(request.COOKIES.get('auth_token'))

    #TODO: Validar se o horario agendado é realmente de un mentor do mentorado
    
    if request.method == 'GET':
        data = request.GET.get('data')
        data = datetime.strptime(data, '%d-%m-%y')
        mentorado = valida_token(request.COOKIES.get('auth_token'))
        horarios = DisponibilidadeHorarios.objects.filter(
            data_inicial__gte=data,
            data_inicial__lt=data + timedelta(days=1),
            agendado=False,
            mentor=mentorado.user
        )
        return render(request, 'agendar_reuniao.html', {'horarios': horarios, 'tags': Reuniao.tag_choices})
    else:
        horario_id = request.POST.get('horario')
        tag = request.POST.get('tag')
        descricao = request.POST.get('descricao')

        # Estudar ATOMICIDADE

        reuniao = Reuniao(
            data_id = horario_id,
            mentorado=mentorado,
            tag=tag,
            descricao=descricao
        )
        reuniao.save()

        horario = DisponibilidadeHorarios.objects.get(id=horario_id)
        horario.agendado = True
        horario.save()

        messages.add_message(request, constants.SUCCESS, 'Reunião agendade com sucesso!!')
        return redirect('escolher_dia')
    
def tarefa(request, id):
    mentorado = Mentorados.objects.get(id=id)
    if mentorado.user != request.user:
        raise Http404()
    
    if request.method == 'GET':
        tarefas = Tarefa.objects.filter(mentorado=mentorado)
        videos = Upload.objects.filter(mentorado=mentorado)
        return render(request, 'tarefa.html', {'mentorado': mentorado, 'tarefas': tarefas,
        'videos': videos})
        
    else:
        tarefa = request.POST.get('tarefa')

        t = Tarefa(
        mentorado = mentorado,
        tarefa = tarefa
        )
        t.save()
        return redirect(f'/mentorados/tarefa/{mentorado.id}')
    
def upload(request, id):
    mentorado = Mentorados.objects.get(id=id)
    if mentorado.user != request.user:
        raise Http404()
    
    video = request.FILES.get('video')
    upload = Upload(
        mentorado=mentorado,
        video=video
    )
    upload.save()
    return redirect(f'/mentorados/tarefa/{mentorado.id}')

def tarefa_mentorado(request):
    mentorado = valida_token(request.COOKIES.get('auth_token'))
    if not mentorado:
        return redirect('auth_mentorado')
    
    if request.method == 'GET':
        videos = Upload.objects.filter(mentorado=mentorado)
        tarefas = Tarefa.objects.filter(mentorado=mentorado)
        return render(request, 'tarefa_mentorado.html', {'mentorado': mentorado, 'videos': videos,
        'tarefas': tarefas})

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def tarefa_alterar(request, id):
    tarefa = Tarefa.objects.get(id=id)

    tarefa.realizada = not tarefa.realizada
    tarefa.save()
