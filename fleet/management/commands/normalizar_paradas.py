from django.core.management.base import BaseCommand
from fleet.models import Parada
from itineraries.models import DetalleItinerario
from operations.models import Encomienda
from django.db import transaction
import unicodedata
import re

def normalize_string(text):
    if not text:
        return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()
    text = text.replace('(', ' ').replace(')', ' ')
    text = re.sub(r'\b(terminal|parada|de)\b', ' ', text)
    return ' '.join(text.split())

class Command(BaseCommand):
    help = 'Normaliza los nombres de paradas y unifica duplicados: "Localidad" para normales, "Localidad (Terminal)" para agencias'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando normalización de paradas...")
        
        localidades = Parada.objects.exclude(localidad__isnull=True).values_list('localidad_id', flat=True).distinct()
        
        for loc_id in localidades:
            paradas = Parada.objects.filter(localidad_id=loc_id).order_by('id')
            
            terminales = []
            otras = []
            
            for p in paradas:
                if 'terminal' in p.nombre.lower() or 'parada' in p.nombre.lower() or p.es_agencia:
                    terminales.append(p)
                else:
                    otras.append(p)
            
            # 1. Unificar terminales -> "Localidad (Terminal)"
            if terminales:
                primaria = terminales[0]
                secundarias = terminales[1:]
                
                nuevo_nombre = f"{primaria.localidad.nombre} (Terminal)"
                
                try:
                    with transaction.atomic():
                        primaria.nombre = nuevo_nombre
                        primaria.es_agencia = True
                        primaria.save()
                        self.stdout.write(self.style.SUCCESS(f"Establecida terminal principal: '{primaria.nombre}'"))
                        
                        for sec in secundarias:
                            self.stdout.write(f"Unificando terminal '{sec.nombre}' -> '{primaria.nombre}'")
                            DetalleItinerario.objects.filter(parada=sec).update(parada=primaria)
                            Encomienda.objects.filter(parada_origen=sec).update(parada_origen=primaria)
                            Encomienda.objects.filter(parada_destino=sec).update(parada_destino=primaria)
                            sec.delete()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error unificando terminal {nuevo_nombre}: {e}"))
            
            # 2. Unificar otras paradas -> "Localidad"
            if otras:
                primaria = otras[0]
                secundarias = otras[1:]
                
                nuevo_nombre = f"{primaria.localidad.nombre}"
                
                try:
                    with transaction.atomic():
                        primaria.nombre = nuevo_nombre
                        primaria.es_agencia = False
                        primaria.save()
                        self.stdout.write(self.style.SUCCESS(f"Establecida parada principal: '{primaria.nombre}'"))
                        
                        for sec in secundarias:
                            self.stdout.write(f"Unificando parada '{sec.nombre}' -> '{primaria.nombre}'")
                            DetalleItinerario.objects.filter(parada=sec).update(parada=primaria)
                            Encomienda.objects.filter(parada_origen=sec).update(parada_origen=primaria)
                            Encomienda.objects.filter(parada_destino=sec).update(parada_destino=primaria)
                            sec.delete()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error unificando parada {nuevo_nombre}: {e}"))
                        
        self.stdout.write(self.style.SUCCESS("Normalización finalizada con éxito."))
