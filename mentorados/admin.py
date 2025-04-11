from django.contrib import admin
from .models import Navigators, Mentorados, DisponibilidadeHorarios, Reuniao

admin.site.register(Navigators)
admin.site.register(Mentorados)
admin.site.register(DisponibilidadeHorarios)
admin.site.register(Reuniao)
