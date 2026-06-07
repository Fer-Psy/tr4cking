from django.core.management.base import BaseCommand
from itineraries.models import Itinerario

class Command(BaseCommand):
    help = 'Check DB for Itinerario'

    def handle(self, *args, **options):
        it = Itinerario.objects.filter(nombre__icontains='Ciudad del Este', empresa__nombre__icontains='Guaireña').first()
        if it:
            self.stdout.write(f'Itinerario: {it.nombre} - Horarios: {[h.hora_salida for h in it.horarios.all()]}')
            self.stdout.write(f'ID: {it.id}')
            self.stdout.write(f'Empresa: {it.empresa.nombre}')
        else:
            self.stdout.write('Not found')
