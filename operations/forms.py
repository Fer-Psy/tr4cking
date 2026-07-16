"""
Formularios para la app Operations.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from .models import (
    Viaje, Pasaje, Encomienda, Timbrado, Factura, 
    DetalleFactura, SesionCaja, MovimientoCaja, Incidencia
)
from .utils import obtener_asientos_disponibles, obtener_orden_parada
from fleet.models import Parada, Empresa, Bus
from users.models import Persona
from itineraries.models import Itinerario, Precio, Horario


# =============================================================================
# VIAJES
# =============================================================================

class ViajeForm(forms.ModelForm):
    """Formulario para crear/editar viajes."""
    
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all(),
        required=False,
        label="Filtrar por Empresa",
        empty_label="-- Todas las Empresas --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Viaje
        fields = ['empresa', 'itinerario', 'horario', 'fecha_viaje', 'bus', 'chofer', 'ayudantes', 'observaciones']
        widgets = {
            'fecha_viaje': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'ayudantes': forms.SelectMultiple(
                attrs={'class': 'form-select', 'data-placeholder': 'Seleccione ayudantes...'}
            ),
            'observaciones': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from crispy_forms.helper import FormHelper

        # Filtrar solo itinerarios activos
        self.fields['itinerario'].queryset = Itinerario.objects.filter(activo=True)
        
        # Inicialmente el queryset de horarios vacío si no hay itinerario
        self.fields['horario'].queryset = Horario.objects.none()
        self.fields['horario'].required = True
        
        # Filtros iniciales base para personal
        self.fields['chofer'].queryset = Persona.objects.filter(es_chofer=True).order_by('apellido', 'nombre')
        self.fields['ayudantes'].queryset = Persona.objects.filter(es_ayudante=True).order_by('apellido', 'nombre')
        
        # Obtener valores actuales (de la instancia o del POST)
        itinerario_id = None
        empresa_id = None
        
        if self.instance and self.instance.pk:
            itinerario_id = self.instance.itinerario_id
            if self.instance.empresa_id:
                empresa_id = self.instance.empresa_id
                self.fields['empresa'].initial = empresa_id
            elif self.instance.itinerario and self.instance.itinerario.empresa:
                empresa_id = self.instance.itinerario.empresa_id
                self.fields['empresa'].initial = empresa_id
        
        val_it = self.data.get('itinerario') or self.initial.get('itinerario')
        if val_it:
            itinerario_id = getattr(val_it, 'pk', val_it)

        val_emp = self.data.get('empresa') or self.initial.get('empresa')
        if val_emp:
            empresa_id = getattr(val_emp, 'pk', val_emp)
        
        # Si tenemos itinerario pero no empresa, intentar obtenerla del itinerario
        if itinerario_id and not empresa_id:
            try:
                it_obj = Itinerario.objects.get(pk=int(itinerario_id))
                if it_obj.empresa:
                    empresa_id = it_obj.empresa_id
                    self.fields['empresa'].initial = empresa_id
            except (ValueError, TypeError, Itinerario.DoesNotExist):
                pass
        
        # Filtrar por empresa si está seleccionada
        if empresa_id:
            try:
                from django.db.models import Q
                emp_id = int(empresa_id)
                self.fields['itinerario'].queryset = Itinerario.objects.filter(
                    empresa_id=emp_id,
                    activo=True
                )
                bus_qs = Bus.objects.filter(empresa_id=emp_id)
                if self.instance and self.instance.pk and self.instance.bus_id:
                    bus_qs = bus_qs.filter(Q(estado='activo') | Q(id=self.instance.bus_id))
                else:
                    bus_qs = bus_qs.filter(estado='activo')
                self.fields['bus'].queryset = bus_qs.order_by('placa')
                self.fields['chofer'].queryset = Persona.objects.filter(
                    Q(es_chofer=True),
                    empresa_id=emp_id
                ).order_by('apellido', 'nombre')
                self.fields['ayudantes'].queryset = Persona.objects.filter(
                    Q(es_ayudante=True),
                    empresa_id=emp_id
                ).order_by('apellido', 'nombre')
            except (ValueError, TypeError):
                pass

        if itinerario_id:
            try:
                it_id = int(itinerario_id)
                itinerario_obj = Itinerario.objects.get(pk=it_id)
                
                # Permitir seleccionar horarios activos asignados al itinerario
                horarios_qs = itinerario_obj.horarios.filter(activo=True)
                
                # Asegurar que el horario actual del viaje esté incluido (por si se desactivó)
                if self.instance and self.instance.pk and self.instance.horario:
                    horarios_qs = horarios_qs | Horario.objects.filter(pk=self.instance.horario.pk)
                    
                self.fields['horario'].queryset = horarios_qs.distinct().order_by('hora_salida')
                self.fields['horario'].required = True
                
                # Si no se seleccionó empresa explícitamente, filtrar por la empresa del itinerario
                if not empresa_id and itinerario_obj.empresa:
                    bus_qs = Bus.objects.filter(empresa=itinerario_obj.empresa)
                    if self.instance and self.instance.pk and self.instance.bus_id:
                        bus_qs = bus_qs.filter(Q(estado='activo') | Q(id=self.instance.bus_id))
                    else:
                        bus_qs = bus_qs.filter(estado='activo')
                    self.fields['bus'].queryset = bus_qs.order_by('placa')
                    self.fields['chofer'].queryset = Persona.objects.filter(
                        Q(es_chofer=True),
                        empresa=itinerario_obj.empresa
                    ).order_by('apellido', 'nombre')
                    self.fields['ayudantes'].queryset = Persona.objects.filter(
                        Q(es_ayudante=True),
                        empresa=itinerario_obj.empresa
                    ).order_by('apellido', 'nombre')
            except (ValueError, TypeError, Itinerario.DoesNotExist):
                pass
        
        # Widgets: todos los selects con form-select, sin Select2 (modales se manejan en template)
        self.fields['empresa'].widget.attrs['class'] = 'form-select'
        self.fields['empresa'].widget.attrs['id'] = 'id_empresa'
        self.fields['horario'].widget.attrs['class'] = 'form-select'
        self.fields['horario'].widget.attrs['id'] = 'id_horario'
        
        # Los campos itinerario, bus, chofer, ayudantes se renderizan como hidden en el template
        # (la selección se hace via modal). Pero necesitan estar en el form para validación.
        for field_name in ['itinerario', 'bus', 'chofer']:
            self.fields[field_name].widget = forms.HiddenInput()
        self.fields['ayudantes'].widget = forms.MultipleHiddenInput()
        
        # Minimal crispy helper (no layout - template handles it)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.disable_csrf = True


    def clean(self):
        cleaned_data = super().clean()
        itinerario = cleaned_data.get('itinerario')
        empresa = cleaned_data.get('empresa')
        
        if itinerario and not empresa:
            cleaned_data['empresa'] = itinerario.empresa
        
        horario = cleaned_data.get('horario')
        bus = cleaned_data.get('bus')
        fecha = cleaned_data.get('fecha_viaje')
        
        # Validar que no sea una fecha pasada
        ahora = timezone.localtime(timezone.now())
        hoy = ahora.date()
        
        if fecha:
            if fecha < hoy:
                raise ValidationError("No se puede programar un viaje en una fecha que ya pasó.")
            
            if fecha == hoy and horario:
                # Comparar hora
                if horario.hora_salida < ahora.time():
                    raise ValidationError(
                        f"El horario seleccionado ({horario.hora_salida.strftime('%H:%M')}) "
                        f"ya no es válido para el día de hoy, porque esa hora ya pasó."
                    )
        
        # Ya no validamos que el horario pertenezca exclusivamente al itinerario
        # ya que los horarios son globales.
        
        # Validaciones de asignación de recursos
        exclude_kwargs = {}
        if self.instance and self.instance.pk:
            exclude_kwargs['pk'] = self.instance.pk

        if itinerario and horario and fecha:
            exists = Viaje.objects.filter(
                itinerario=itinerario,
                horario=horario,
                fecha_viaje=fecha
            ).exclude(**exclude_kwargs).exclude(estado='cancelado').exists()
            
            if exists:
                raise ValidationError("Ya existe un viaje programado para este itinerario, horario y fecha.")
        
        if bus and bus.estado != 'activo':
            if not self.instance.pk or self.instance.bus_id != bus.id:
                raise ValidationError({"bus": "El bus seleccionado no está activo (en mantenimiento o inactivo) y no puede ser asignado."})
        
        if bus and horario and fecha:
            bus_exists = Viaje.objects.filter(
                bus=bus,
                horario=horario,
                fecha_viaje=fecha
            ).exclude(**exclude_kwargs).exclude(estado='cancelado').exists()
            
            if bus_exists:
                raise ValidationError("Este bus ya está asignado a otro viaje en este horario y fecha.")
        
        chofer = cleaned_data.get('chofer')
        if chofer and fecha and horario:
            chofer_exists = Viaje.objects.filter(
                chofer=chofer,
                horario=horario,
                fecha_viaje=fecha
            ).exclude(**exclude_kwargs).exclude(estado='cancelado').exists()
            
            if chofer_exists:
                raise ValidationError(f"El chofer {chofer.get_full_name()} ya tiene asignado un viaje en esta fecha y horario.")
        
        ayudantes = cleaned_data.get('ayudantes')
        if ayudantes and fecha and horario:
            for ayudante in ayudantes:
                ayudante_exists = Viaje.objects.filter(
                    ayudantes=ayudante,
                    horario=horario,
                    fecha_viaje=fecha
                ).exclude(**exclude_kwargs).exclude(estado='cancelado').exists()
                
                if ayudante_exists:
                    raise ValidationError(f"El ayudante {ayudante.get_full_name()} ya tiene asignado un viaje en esta fecha y horario.")

        # Función auxiliar para validar secuencia lógica (descanso y ruta)
        from datetime import datetime, timedelta
        def validar_secuencia(recurso, campo, nombre_recurso):
            if not recurso or not fecha or not horario or not itinerario:
                return
            
            nuevo_salida_dt = timezone.make_aware(datetime.combine(fecha, horario.hora_salida))
            
            query = Viaje.objects.filter(estado__in=['programado', 'en_curso', 'completado']).exclude(**exclude_kwargs)
            if campo == 'ayudantes':
                query = query.filter(ayudantes=recurso)
            else:
                query = query.filter(**{campo: recurso})
            
            # Buscar el último viaje anterior a este
            last_trip = query.filter(
                Q(fecha_viaje__lt=fecha) | 
                Q(fecha_viaje=fecha, horario__hora_salida__lt=horario.hora_salida)
            ).order_by('-fecha_viaje', '-horario__hora_salida').first()
            
            # Solo aplicamos esta validación estricta al crear un viaje nuevo, 
            # para evitar que salte error al simplemente editar la hora de un viaje existente.
            if not self.instance.pk and last_trip and last_trip.itinerario == itinerario:
                raise ValidationError(f"{nombre_recurso} ({recurso}) acaba de realizar este mismo trayecto. Por lógica operativa, no puede hacer el mismo itinerario de ida dos veces seguidas sin haber hecho un viaje de regreso, ya que físicamente se encuentra en el destino.")
            
            # Viajes en el MISMO DÍA (fecha)
            viajes_dia = query.filter(fecha_viaje=fecha).order_by('horario__hora_salida')
            
            if viajes_dia.exists():
                if campo in ['chofer', 'ayudantes']:
                    # Chofer y ayudante solo un viaje por día
                    raise ValidationError(f"{nombre_recurso} ({recurso}) solo puede realizar un solo viaje en el día.")
                elif campo == 'bus':
                    # El bus puede hacer ida y vuelta (máximo 2 viajes en el día)
                    if viajes_dia.count() >= 2:
                        raise ValidationError(f"El bus ({recurso}) ya tiene programados 2 viajes (ida y vuelta) para este día.")
                    
                    # Validar que el segundo viaje sea DESPUÉS de 4 horas del otro viaje
                    viaje_existente = viajes_dia.first()
                    if viaje_existente.horario:
                        salida_existente_dt = timezone.make_aware(datetime.combine(fecha, viaje_existente.horario.hora_salida))
                        
                        # Diferencia absoluta en horas
                        diff = abs((nuevo_salida_dt - salida_existente_dt).total_seconds()) / 3600
                        if diff < 4:
                            raise ValidationError(f"El bus ({recurso}) debe esperar al menos 4 horas para realizar su viaje de retorno (El primer viaje es a las {salida_existente_dt.strftime('%H:%M')}).")

        validar_secuencia(bus, 'bus', 'El bus')
        validar_secuencia(chofer, 'chofer', 'El chofer')
        if ayudantes:
            for ayudante in ayudantes:
                validar_secuencia(ayudante, 'ayudantes', 'El ayudante')

        return cleaned_data


class ViajeEstadoForm(forms.ModelForm):
    """Formulario para cambiar estado de viaje."""
    
    class Meta:
        model = Viaje
        fields = ['estado', 'hora_salida_real', 'hora_llegada_real', 'observaciones']
        widgets = {
            'hora_salida_real': forms.TimeInput(
                attrs={'type': 'time', 'class': 'form-control'}
            ),
            'hora_llegada_real': forms.TimeInput(
                attrs={'type': 'time', 'class': 'form-control'}
            ),
            'observaciones': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),
        }


# =============================================================================
# PASAJES
# =============================================================================

class PasajeVentaForm(forms.ModelForm):
    """Formulario para venta de pasajes con disponibilidad por segmento."""
    
    cedula_pasajero = forms.IntegerField(
        label="Cédula del Pasajero",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de cédula',
            'hx-get': '/operations/buscar-persona/',
            'hx-trigger': 'blur',
            'hx-target': '#info-pasajero',
            'hx-swap': 'innerHTML',
            'hx-vals': 'js:{cedula: document.getElementById("id_cedula_pasajero").value}'
        })
    )
    
    cedula_cliente = forms.IntegerField(
        label="Cédula del Cliente (quien paga)",
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Dejar vacío si es el mismo pasajero',
            'hx-get': '/operations/buscar-persona/',
            'hx-trigger': 'blur',
            'hx-target': '#info-cliente',
            'hx-swap': 'innerHTML',
            'hx-vals': 'js:{cedula: document.getElementById("id_cedula_cliente").value}'
        })
    )

    # Campos del Pasajero (para crear nuevo si no existe)
    nombre_pasajero = forms.CharField(
        label="Nombre del Pasajero",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre'
        })
    )
    
    apellido_pasajero = forms.CharField(
        label="Apellido del Pasajero",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido'
        })
    )
    
    telefono_pasajero = forms.CharField(
        label="Teléfono del Pasajero",
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de teléfono'
        })
    )

    class Meta:
        model = Pasaje
        fields = ['viaje', 'asiento', 'parada_origen', 'parada_destino', 'precio']
        widgets = {
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el precio'
            }),
        }

    def __init__(self, *args, viaje=None, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        
        if viaje:
            self.fields['viaje'].initial = viaje
            self.fields['viaje'].widget = forms.HiddenInput()
            
            # Filtrar paradas del itinerario
            paradas_ids = viaje.itinerario.detalles.values_list('parada_id', flat=True)
            paradas_queryset = Parada.objects.filter(id__in=list(paradas_ids)).order_by('nombre')
            self.fields['parada_origen'].queryset = paradas_queryset
            self.fields['parada_destino'].queryset = paradas_queryset
            
            # Inicialmente mostrar todos los asientos del bus
            # (se refiltra dinámicamente vía AJAX cuando se seleccionan origen/destino)
            self.fields['asiento'].queryset = viaje.bus.asientos.all().order_by('numero_asiento')
        
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-select' if isinstance(
                    field, forms.ModelChoiceField
                ) else 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        origen = cleaned_data.get('parada_origen')
        destino = cleaned_data.get('parada_destino')
        viaje = cleaned_data.get('viaje')
        asiento = cleaned_data.get('asiento')
        
        if origen and destino and origen == destino:
            raise ValidationError("El origen y destino no pueden ser iguales.")
        
        # Validar disponibilidad por segmento
        if viaje and asiento and origen and destino:
            orden_origen = obtener_orden_parada(viaje, origen)
            orden_destino = obtener_orden_parada(viaje, destino)
            
            if orden_origen is None or orden_destino is None:
                raise ValidationError("Las paradas seleccionadas no pertenecen a este itinerario.")
            
            if orden_origen >= orden_destino:
                raise ValidationError("La parada de origen debe ser anterior a la de destino en el recorrido.")
            
            # Verificar disponibilidad del asiento en el tramo
            from .utils import asiento_disponible_en_tramo
            
            # Solo agentes, empleados y superusuarios pueden "vender sobre ocupado"
            # Los ayudantes/choferes NO pueden vender sobre un asiento ya vendido por un agente
            persona_vendedor = getattr(self.user, 'persona', None) if self.user else None
            puede_overbooking = self.user and (
                self.user.is_superuser or 
                (persona_vendedor and persona_vendedor.es_agente and not persona_vendedor.es_ayudante and not persona_vendedor.es_chofer)
            )
            
            if not asiento_disponible_en_tramo(viaje, asiento, orden_origen, orden_destino):
                # Verificar si el conflicto es con una RESERVA hecha por sistema/clientes
                conflictos_reserva = Pasaje.objects.filter(
                    viaje=viaje,
                    asiento=asiento,
                    estado='reservado',
                    orden_origen__lt=orden_destino,
                    orden_destino__gt=orden_origen,
                )
                
                if conflictos_reserva.exists():
                    raise ValidationError(
                        f"El asiento {asiento.numero_asiento} tiene una RESERVA ACTIVA en este tramo. "
                        "No puede ser vendido."
                    )
                
                # Para usuarios sin permiso de overbooking general (como el ayudante)
                if not puede_overbooking:
                    es_ayudante = persona_vendedor and (persona_vendedor.es_ayudante or persona_vendedor.es_chofer)
                    
                    if es_ayudante:
                        # Buscar conflictos con pasajes vendidos por otros usuarios
                        conflictos_otros = Pasaje.objects.filter(
                            viaje=viaje,
                            asiento=asiento,
                            estado__in=['vendido', 'abordado'],
                            orden_origen__lt=orden_destino,
                            orden_destino__gt=orden_origen,
                        ).exclude(vendedor=self.user)
                        
                        if conflictos_otros.exists():
                            raise ValidationError(
                                f"El asiento {asiento.numero_asiento} ya está vendido en este tramo por otro vendedor. "
                                "Solo puede vender sobre sus propias ventas o si es administrador/agente de ventas."
                            )
                    else:
                        raise ValidationError(
                            f"El asiento {asiento.numero_asiento} ya está vendido en este tramo. "
                            "Solo un agente de ventas o administrador puede reasignar este asiento."
                        )
                # Si es agente/admin y el conflicto es solo con vendidos/abordados, permitimos continuar
            
            # Guardar los órdenes para uso posterior en la vista
            cleaned_data['orden_origen'] = orden_origen
            cleaned_data['orden_destino'] = orden_destino
            
            # Normalizar paradas para que coincidan con el itinerario del viaje
            # Esto evita guardar IDs de paradas de "Guaireña" en viajes de "Ybyturuzu" (o viceversa)
            from itineraries.models import DetalleItinerario
            detalle_o = DetalleItinerario.objects.filter(itinerario=viaje.itinerario, orden=orden_origen).first()
            detalle_d = DetalleItinerario.objects.filter(itinerario=viaje.itinerario, orden=orden_destino).first()
            if detalle_o:
                cleaned_data['parada_origen'] = detalle_o.parada
            if detalle_d:
                cleaned_data['parada_destino'] = detalle_d.parada
        
        return cleaned_data


class PasajeCancelacionForm(forms.Form):
    """Formulario para cancelar un pasaje."""
    
    motivo = forms.CharField(
        label="Motivo de cancelación",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'required': True
        })
    )
    devolver_dinero = forms.BooleanField(
        label="¿Devolver dinero?",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


# =============================================================================
# ENCOMIENDAS
# =============================================================================

class EncomiendaForm(forms.ModelForm):
    """Formulario para registrar encomiendas."""
    
    # Campo oculto para remitente seleccionado desde el modal
    remitente_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_remitente_id'})
    )
    
    cedula_remitente = forms.IntegerField(
        label="Cédula del Remitente",
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese cédula o busque en el listado',
            'readonly': 'readonly'
        })
    )
    
    # Campos del destinatario (para crear nuevo si no existe)
    cedula_destinatario = forms.IntegerField(
        label="Cédula del Destinatario (Opcional)",
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Dejar vacío si no tiene'
        })
    )
    
    nombre_destinatario = forms.CharField(
        label="Nombre del Destinatario",
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre'
        })
    )
    
    apellido_destinatario = forms.CharField(
        label="Apellido del Destinatario",
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido'
        })
    )
    
    telefono_destinatario = forms.CharField(
        label="Teléfono del Destinatario",
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de teléfono'
        })
    )
    
    direccion_destinatario = forms.CharField(
        label="Dirección del Destinatario",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Dirección de entrega'
        })
    )
    
    dimensiones = forms.CharField(
        label="Dimensiones (opcional)",
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 30x20x15 cm'
        })
    )

    class Meta:
        model = Encomienda
        fields = [
            'viaje', 'parada_origen', 'parada_destino',
            'tipo', 'descripcion', 'peso_kg', 'precio'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describa el contenido de la encomienda'
            }),
            'peso_kg': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Peso en kg'
            }),
            'precio': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Precio en Gs.'
            }),
        }
        error_messages = {
            'viaje': {
                'required': "Debe seleccionar un bus/viaje disponible para registrar la encomienda.",
            }
        }

    def __init__(self, *args, viaje=None, empresa=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if viaje:
            # Si viene de un viaje específico, ocultarlo
            self.fields['viaje'].initial = viaje
            self.fields['viaje'].widget = forms.HiddenInput()
            
            # Filtrar paradas del itinerario
            paradas_ids = viaje.itinerario.detalles.values_list('parada_id', flat=True)
            paradas_queryset = Parada.objects.filter(id__in=list(paradas_ids), es_agencia=True).order_by('nombre')
            self.fields['parada_origen'].queryset = paradas_queryset
            self.fields['parada_destino'].queryset = paradas_queryset
        else:
            # Si es creación directa, mostrar selector de viajes con info del bus
            self.fields['parada_origen'].queryset = Parada.objects.filter(es_agencia=True).order_by('nombre')
            self.fields['parada_destino'].queryset = Parada.objects.filter(es_agencia=True).order_by('nombre')
            from django.utils import timezone
            from django.db.models import Q
            
            ahora = timezone.localtime(timezone.now())
            hoy = ahora.date()
            hora_actual = ahora.time()
            
            # Mostrar viajes programados o en curso de hoy en adelante.
            # No filtramos por la hora_salida exacta porque la hora_salida es del origen inicial,
            # y las agencias intermedias (ej. Oviedo) necesitan ver el viaje aunque ya haya salido de Asunción.
            viajes_disponibles = Viaje.objects.filter(
                fecha_viaje__gte=hoy,
                estado__in=['programado', 'en_curso']
            ).select_related(
                'itinerario', 'bus', 'horario'
            ).prefetch_related(
                'itinerario__detalles'
            ).order_by('fecha_viaje', 'itinerario__nombre')
            
            if empresa:
                viajes_disponibles = viajes_disponibles.filter(
                    Q(empresa=empresa) | Q(bus__empresa=empresa)
                )
            
            # Restricción para ayudantes y choferes
            persona = getattr(user, 'persona', None) if user else None
            if persona and (persona.es_ayudante or persona.es_chofer) and not user.is_superuser:
                viajes_disponibles = viajes_disponibles.filter(
                    Q(chofer=persona) | Q(ayudantes=persona)
                )
            
            self.fields['viaje'].queryset = viajes_disponibles
            
            def get_viaje_label(obj):
                # Obtener hora de salida del horario asignado al viaje
                hora_str = obj.horario.hora_salida.strftime('%H:%M') if obj.horario else 'Sin horario'
                empresa_nombre = obj.empresa.nombre if obj.empresa else (obj.bus.empresa.nombre if obj.bus.empresa else "Sin Empresa")
                return (
                    f"{obj.fecha_viaje.strftime('%d/%m/%Y')} - {empresa_nombre} - {obj.itinerario.nombre} - "
                    f"Bus: {obj.bus.placa} ({hora_str})"
                )
            
            self.fields['viaje'].label_from_instance = get_viaje_label
            self.fields['viaje'].widget.attrs.update({
                'class': 'form-select',
                'id': 'id_viaje'
            })
            self.fields['viaje'].empty_label = "-- Seleccione un viaje --"
        
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-select' if isinstance(
                    field, forms.ModelChoiceField
                ) else 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        viaje = cleaned_data.get('viaje')
        origen = cleaned_data.get('parada_origen')
        destino = cleaned_data.get('parada_destino')
        
        if origen and destino and origen == destino:
            raise ValidationError("El origen y destino no pueden ser iguales.")
            
        if viaje and origen and destino:
            from .utils import obtener_orden_parada
            orden_origen = obtener_orden_parada(viaje, origen)
            orden_destino = obtener_orden_parada(viaje, destino)
            
            if orden_origen is None or orden_destino is None:
                raise ValidationError("Las paradas seleccionadas no pertenecen a este itinerario.")
            
            if orden_origen >= orden_destino:
                raise ValidationError("La parada de origen debe ser anterior a la de destino.")
            
            # Normalizar paradas para que coincidan con el itinerario del viaje
            from itineraries.models import DetalleItinerario
            detalle_o = DetalleItinerario.objects.filter(itinerario=viaje.itinerario, orden=orden_origen).first()
            detalle_d = DetalleItinerario.objects.filter(itinerario=viaje.itinerario, orden=orden_destino).first()
            if detalle_o:
                cleaned_data['parada_origen'] = detalle_o.parada
            if detalle_d:
                cleaned_data['parada_destino'] = detalle_d.parada
                
        return cleaned_data


class EncomiendaEntregaForm(forms.Form):
    """Formulario para entregar una encomienda."""
    
    receptor_nombre = forms.CharField(
        label="Nombre de quien recibe",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    receptor_cedula = forms.CharField(
        label="Cédula de quien recibe (Opcional)",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    receptor_telefono = forms.CharField(
        label="Teléfono de quien recibe (Opcional)",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )


# =============================================================================
# TIMBRADOS
# =============================================================================

class TimbradoForm(forms.ModelForm):
    """Formulario para timbrados fiscales."""
    
    class Meta:
        model = Timbrado
        fields = [
            'empresa', 'numero', 'fecha_inicio', 'fecha_fin',
            'numero_desde', 'numero_hasta', 'punto_expedicion', 'activo'
        ]
        widgets = {
            'fecha_inicio': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'fecha_fin': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'punto_expedicion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 001-001'
            }),
            'numero_desde': forms.NumberInput(attrs={'class': 'form-control'}),
            'numero_hasta': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field, forms.BooleanField):
                    field.widget.attrs['class'] = 'form-check-input'
                elif isinstance(field, forms.ModelChoiceField):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'
    
    def clean(self):
        cleaned_data = super().clean()
        empresa = cleaned_data.get('empresa')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        numero_desde = cleaned_data.get('numero_desde')
        numero_hasta = cleaned_data.get('numero_hasta')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            from django.core.exceptions import ValidationError
            raise ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")
        
        if numero_desde and numero_hasta and numero_desde > numero_hasta:
            from django.core.exceptions import ValidationError
            raise ValidationError("El número inicial debe ser menor al número final.")
            
        if empresa and fecha_inicio and fecha_fin:
            from django.core.exceptions import ValidationError
            from django.utils import timezone
            
            existing = Timbrado.objects.filter(empresa=empresa)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
                
            for t in existing:
                if fecha_inicio <= t.fecha_fin and fecha_fin >= t.fecha_inicio:
                    raise ValidationError(
                        f"Las fechas de vigencia se superponen con el timbrado N° {t.numero} "
                        f"válido desde {t.fecha_inicio.strftime('%d/%m/%Y')} "
                        f"hasta {t.fecha_fin.strftime('%d/%m/%Y')}."
                    )
            
            # Check for existing active timbrado for Programador restriction
            if not self.instance.pk: # Only for creation
                now = timezone.now().date()
                active_timbrados = existing.filter(activo=True, fecha_fin__gte=now)
                if active_timbrados.exists():
                    if not self.user or not self.user.is_superuser:
                        raise ValidationError("Solo los Programadores pueden crear un nuevo timbrado si ya existe uno vigente y no vencido para esta empresa.")
        
        return cleaned_data


# =============================================================================
# FACTURACIÓN
# =============================================================================

class FacturaForm(forms.ModelForm):
    """
    Formulario para crear facturas desde pasajes o encomiendas.
    """
    
    cedula_cliente = forms.IntegerField(
        label="Cédula/RUC del Cliente",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de cédula o RUC',
            'hx-get': '/operations/buscar-persona/',
            'hx-trigger': 'blur',
            'hx-target': '#info-cliente-factura',
            'hx-swap': 'innerHTML',
            'hx-vals': 'js:{cedula: document.getElementById("id_cedula_cliente").value}'
        })
    )
    
    # Campos para seleccionar items a facturar
    pasajes = forms.ModelMultipleChoiceField(
        queryset=Pasaje.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="Pasajes a facturar"
    )
    
    encomiendas = forms.ModelMultipleChoiceField(
        queryset=Encomienda.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="Encomiendas a facturar"
    )
    
    class Meta:
        model = Factura
        fields = ['timbrado', 'condicion']
        widgets = {
            'condicion': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, cliente=None, pasaje=None, encomienda=None, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        
        # Forzar condición a contado y bloquear el campo
        self.fields['condicion'].initial = 'contado'
        self.fields['condicion'].disabled = True
        
        # Solo timbrados activos y vigentes
        hoy = timezone.now().date()
        self.fields['timbrado'].queryset = Timbrado.objects.filter(
            activo=True,
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        
        # Identificar si el usuario es ayudante o chofer
        es_ayudante_o_chofer = False
        if user:
            persona = getattr(user, 'persona', None)
            es_ayudante_o_chofer = persona and (persona.es_ayudante or persona.es_chofer) and not user.is_superuser

        # Convertir cliente a int si viene como string
        cliente_cedula = None
        if cliente:
            if isinstance(cliente, str):
                # Limpiar espacios y caracteres de formato
                cliente_limpio = cliente.replace(' ', '').replace('\xa0', '').replace('.', '')
                try:
                    cliente_cedula = int(cliente_limpio)
                except (ValueError, TypeError):
                    cliente_cedula = None
            else:
                cliente_cedula = cliente
        
        # Identificar empresa para pre-seleccionar timbrado
        item_empresa = None
        
        # 1. Cargar Pasajes
        if pasaje:
            self.fields['pasajes'].queryset = Pasaje.objects.filter(pk=pasaje.pk)
            self.fields['pasajes'].initial = [pasaje]
            if pasaje.viaje:
                item_empresa = pasaje.viaje.empresa_operadora
        elif cliente_cedula:
            self.fields['pasajes'].queryset = Pasaje.objects.filter(
                Q(pasajero__cedula=cliente_cedula) | Q(cliente__cedula=cliente_cedula),
                estado__in=['vendido', 'reservado', 'abordado']
            ).exclude(
                detalles_factura__factura__estado='emitida'
            ).select_related('viaje', 'asiento')

        # 2. Cargar Encomiendas (ocultar para ayudantes/choferes)
        if es_ayudante_o_chofer:
            self.fields['encomiendas'].queryset = Encomienda.objects.none()
            self.fields['encomiendas'].widget = forms.HiddenInput()
            self.fields['encomiendas'].label = ""
        elif encomienda:
            self.fields['encomiendas'].queryset = Encomienda.objects.filter(pk=encomienda.pk)
            self.fields['encomiendas'].initial = [encomienda]
            if encomienda.viaje:
                item_empresa = encomienda.viaje.empresa_operadora
        elif cliente_cedula:
            self.fields['encomiendas'].queryset = Encomienda.objects.filter(
                remitente__cedula=cliente_cedula,
                estado__in=['registrado', 'en_transito', 'en_destino', 'entregado']
            ).exclude(
                detalles_factura__factura__estado='emitida'
            ).select_related('viaje', 'parada_destino')
        
        # 3. Pre-seleccionar Timbrado si hay empresa identificada
        if item_empresa and not self.initial.get('timbrado'):
            timbrado_pred = self.fields['timbrado'].queryset.filter(empresa=item_empresa).first()
            if timbrado_pred:
                self.fields['timbrado'].initial = timbrado_pred
                self.fields['timbrado'].widget.attrs['data-empresa-auto'] = item_empresa.id
        
        
        for field_name, field in self.fields.items():
            if field_name not in ['pasajes', 'encomiendas'] and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-select' if isinstance(
                    field, forms.ModelChoiceField
                ) else 'form-control'
    
    def clean(self):
        cleaned_data = super().clean()
        pasajes = cleaned_data.get('pasajes', [])
        encomiendas = cleaned_data.get('encomiendas', [])
        
        # Validar que el usuario tenga caja abierta
        if self.user:
            from .models import SesionCaja
            if not SesionCaja.objects.filter(cajero=self.user, estado='abierta').exists():
                raise ValidationError(
                    "No puede facturar porque no tiene una sesión de caja abierta."
                )
        
        if not pasajes and not encomiendas:
            raise ValidationError(
                "Debe seleccionar al menos un pasaje o encomienda para facturar."
            )
            
        # Validar que todos los items pertenezcan a la misma empresa y que el timbrado corresponda
        empresas = set()
        for p in pasajes:
            if p.viaje and p.viaje.empresa_operadora:
                empresas.add(p.viaje.empresa_operadora)
        for e in encomiendas:
            if e.viaje and e.viaje.empresa_operadora:
                empresas.add(e.viaje.empresa_operadora)
                
        if len(empresas) > 1:
            raise ValidationError("No se pueden facturar ítems de distintas empresas en la misma factura.")
            
        timbrado = cleaned_data.get('timbrado')
        if timbrado and empresas:
            empresa_items = empresas.pop()
            if timbrado.empresa != empresa_items:
                raise ValidationError(f"El timbrado seleccionado ({timbrado.empresa.nombre}) no corresponde a la empresa de los ítems ({empresa_items.nombre}).")
        
        return cleaned_data


class FacturaDesdeVentaForm(forms.Form):
    """
    Formulario simplificado para crear factura directamente desde una venta.
    Se usa cuando se genera factura automáticamente al vender pasaje/encomienda.
    """
    
    generar_factura = forms.BooleanField(
        label="¿Generar factura?",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    tasa_iva = forms.ChoiceField(
        label="Tasa de IVA",
        choices=[
            (0, 'Exenta (0%)'),
            (10, 'IVA 10%'),
        ],
        initial=0,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class FacturaAnulacionForm(forms.Form):
    """Formulario para anular una factura."""
    
    motivo = forms.CharField(
        label="Motivo de anulación",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'required': True
        })
    )
    
    # revertir_caja se aplica siempre automáticamente


# =============================================================================
# CAJA
# =============================================================================

class AperturaCajaForm(forms.Form):
    """Formulario para apertura de caja."""
    
    monto_apertura = forms.DecimalField(
        label="Monto de apertura",
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Gs. 0'
        })
    )
    observaciones = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2
        })
    )


class CierreCajaForm(forms.Form):
    """Formulario para cierre de caja."""
    
    monto_real = forms.DecimalField(
        label="Monto real en caja",
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Gs. 0'
        })
    )
    observaciones = forms.CharField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3
        })
    )


class MovimientoCajaForm(forms.ModelForm):
    """Formulario para movimientos de caja manuales."""
    
    class Meta:
        model = MovimientoCaja
        fields = ['tipo', 'concepto', 'monto', 'descripcion']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, sesion=None, **kwargs):
        self.sesion = sesion
        super().__init__(*args, **kwargs)
        # Limitar conceptos para movimientos manuales
        self.fields['concepto'].choices = [
            ('gasto', 'Gasto'),
            ('retiro', 'Retiro'),
            ('deposito', 'Depósito'),
            ('otro', 'Otro'),
        ]
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-select' if isinstance(
                    field, forms.ChoiceField
                ) else 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        concepto = cleaned_data.get('concepto')
        monto = cleaned_data.get('monto')
        
        if tipo == 'ingreso' and concepto in ['gasto', 'retiro']:
            self.add_error('concepto', "Un ingreso no puede ser un Gasto o Retiro.")
        
        if tipo == 'egreso' and concepto == 'deposito':
            self.add_error('concepto', "Un egreso no puede ser un Depósito.")
            
        if tipo == 'egreso' and monto and self.sesion:
            saldo_actual = self.sesion.calcular_cierre()
            if saldo_actual < monto:
                self.add_error('monto', f"No hay suficiente saldo en caja (Saldo actual: Gs. {saldo_actual}).")
            
        return cleaned_data


# =============================================================================
# INCIDENCIAS
# =============================================================================

class IncidenciaForm(forms.ModelForm):
    """Formulario para registrar incidencias."""
    
    class Meta:
        model = Incidencia
        fields = ['viaje', 'tipo', 'prioridad', 'descripcion']
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
        }

    def __init__(self, *args, viaje=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if viaje:
            self.fields['viaje'].initial = viaje
            self.fields['viaje'].widget = forms.HiddenInput()
        else:
            # Solo viajes activos o recientes
            self.fields['viaje'].queryset = Viaje.objects.filter(
                estado__in=['programado', 'en_curso']
            ).order_by('-fecha_viaje')
        
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-select' if isinstance(
                    field, (forms.ModelChoiceField, forms.ChoiceField)
                ) else 'form-control'


class IncidenciaResolucionForm(forms.Form):
    """Formulario para resolver una incidencia."""
    
    resolucion = forms.CharField(
        label="Resolución",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'required': True
        })
    )


# =============================================================================
# BÚSQUEDA Y FILTROS
# =============================================================================

class BusquedaViajeForm(forms.Form):
    """Formulario para buscar viajes."""
    
    origen = forms.ModelChoiceField(
        queryset=Parada.objects.all(),
        required=False,
        label="Origen",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    destino = forms.ModelChoiceField(
        queryset=Parada.objects.all(),
        required=False,
        label="Destino",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    fecha = forms.DateField(
        required=False,
        label="Fecha",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )


class BusquedaEncomiendaForm(forms.Form):
    """Formulario para buscar encomiendas."""
    
    codigo = forms.CharField(
        required=False,
        label="Código de seguimiento",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ENC-XXXXXXXX-XXXX'
        })
    )
    cedula = forms.IntegerField(
        required=False,
        label="Cédula (remitente o destinatario)",
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos')] + list(Encomienda.ESTADO_CHOICES),
        required=False,
        label="Estado",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
