"""
Formularios para la app Operations.
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Viaje, Pasaje, Encomienda, Timbrado, Factura, 
    DetalleFactura, SesionCaja, MovimientoCaja, Incidencia
)
from fleet.models import Parada
from itineraries.models import Itinerario


# =============================================================================
# VIAJES
# =============================================================================

class ViajeForm(forms.ModelForm):
    """Formulario para crear/editar viajes."""
    
    class Meta:
        model = Viaje
        fields = ['itinerario', 'bus', 'chofer', 'fecha_viaje', 'observaciones']
        widgets = {
            'fecha_viaje': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'observaciones': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo itinerarios activos
        self.fields['itinerario'].queryset = Itinerario.objects.filter(activo=True)
        
        # Aplicar clases Bootstrap
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.Textarea):
                field.widget.attrs['class'] = 'form-select' if isinstance(
                    field, forms.ModelChoiceField
                ) else 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        itinerario = cleaned_data.get('itinerario')
        bus = cleaned_data.get('bus')
        fecha = cleaned_data.get('fecha_viaje')
        
        if itinerario and bus and fecha:
            # Verificar que no exista otro viaje igual
            exists = Viaje.objects.filter(
                itinerario=itinerario,
                bus=bus,
                fecha_viaje=fecha
            ).exclude(pk=self.instance.pk if self.instance else None).exists()
            
            if exists:
                raise ValidationError(
                    "Ya existe un viaje programado para este itinerario, bus y fecha."
                )
        
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
    """Formulario para venta de pasajes."""
    
    cedula_pasajero = forms.IntegerField(
        label="Cédula del Pasajero",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de cédula',
            'hx-get': '/operations/buscar-persona/',
            'hx-trigger': 'blur',
            'hx-target': '#info-pasajero',
            'hx-swap': 'innerHTML',
            'hx-vals': 'js:{cedula: this.value}'
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
            'hx-vals': 'js:{cedula: this.value}'
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

    def __init__(self, *args, viaje=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if viaje:
            self.fields['viaje'].initial = viaje
            self.fields['viaje'].widget = forms.HiddenInput()
            
            # Filtrar asientos disponibles del bus del viaje
            asientos_vendidos = Pasaje.objects.filter(
                viaje=viaje,
                estado__in=['reservado', 'vendido']
            ).values_list('asiento_id', flat=True)
            
            self.fields['asiento'].queryset = viaje.bus.asientos.exclude(
                id__in=asientos_vendidos
            ).order_by('numero_asiento')
            
            # Filtrar paradas del itinerario
            paradas_ids = viaje.itinerario.detalles.values_list('parada_id', flat=True)
            paradas_queryset = Parada.objects.filter(id__in=list(paradas_ids)).order_by('nombre')
            self.fields['parada_origen'].queryset = paradas_queryset
            self.fields['parada_destino'].queryset = paradas_queryset
        
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-select' if isinstance(
                    field, forms.ModelChoiceField
                ) else 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        origen = cleaned_data.get('parada_origen')
        destino = cleaned_data.get('parada_destino')
        
        if origen and destino and origen == destino:
            raise ValidationError("El origen y destino no pueden ser iguales.")
        
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
        label="Cédula del Destinatario",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Número de cédula'
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

    def __init__(self, *args, viaje=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if viaje:
            # Si viene de un viaje específico, ocultarlo
            self.fields['viaje'].initial = viaje
            self.fields['viaje'].widget = forms.HiddenInput()
            
            # Filtrar paradas del itinerario
            paradas_ids = viaje.itinerario.detalles.values_list('parada_id', flat=True)
            paradas_queryset = Parada.objects.filter(id__in=list(paradas_ids)).order_by('nombre')
            self.fields['parada_origen'].queryset = paradas_queryset
            self.fields['parada_destino'].queryset = paradas_queryset
        else:
            # Si es creación directa, mostrar selector de viajes con info del bus
            from django.utils import timezone
            hoy = timezone.now().date()
            
            # Mostrar solo viajes programados o en curso de hoy en adelante
            viajes_disponibles = Viaje.objects.filter(
                fecha_viaje__gte=hoy,
                estado__in=['programado', 'en_curso']
            ).select_related(
                'itinerario', 'bus'
            ).prefetch_related(
                'itinerario__detalles'
            ).order_by('fecha_viaje', 'itinerario__nombre')
            
            self.fields['viaje'].queryset = viajes_disponibles
            
            def get_viaje_label(obj):
                # Obtener hora de salida del primer detalle del itinerario
                primer_detalle = obj.itinerario.detalles.order_by('orden').first()
                hora_str = primer_detalle.hora_salida.strftime('%H:%M') if primer_detalle and primer_detalle.hora_salida else 'Sin hora'
                return (
                    f"{obj.fecha_viaje.strftime('%d/%m/%Y')} - {obj.itinerario.nombre} - "
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


class EncomiendaEntregaForm(forms.Form):
    """Formulario para entregar una encomienda."""
    
    receptor_nombre = forms.CharField(
        label="Nombre de quien recibe",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    receptor_cedula = forms.CharField(
        label="Cédula de quien recibe",
        max_length=20,
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
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-select' if isinstance(
                    field, forms.ModelChoiceField
                ) else 'form-control'
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        numero_desde = cleaned_data.get('numero_desde')
        numero_hasta = cleaned_data.get('numero_hasta')
        
        if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
            raise ValidationError("La fecha de inicio debe ser anterior a la fecha de fin.")
        
        if numero_desde and numero_hasta and numero_desde > numero_hasta:
            raise ValidationError("El número inicial debe ser menor al número final.")
        
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
            'hx-vals': 'js:{cedula: this.value}'
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

    def __init__(self, *args, cliente=None, pasaje=None, encomienda=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Solo timbrados activos y vigentes
        hoy = timezone.now().date()
        self.fields['timbrado'].queryset = Timbrado.objects.filter(
            activo=True,
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        
        # Convertir cliente a int si viene como string
        cliente_cedula = None
        if cliente:
            try:
                cliente_cedula = int(cliente) if isinstance(cliente, str) else cliente
            except (ValueError, TypeError):
                cliente_cedula = None
        
        # Pre-seleccionar pasaje o encomienda si viene de una venta
        if pasaje:
            self.fields['pasajes'].queryset = Pasaje.objects.filter(pk=pasaje.pk)
            self.fields['pasajes'].initial = [pasaje]
        elif cliente_cedula:
            # Pasajes del cliente sin facturar
            self.fields['pasajes'].queryset = Pasaje.objects.filter(
                pasajero__cedula=cliente_cedula,
                estado='vendido'
            ).exclude(
                detalles_factura__factura__estado='emitida'
            ).select_related('viaje', 'asiento')
        
        if encomienda:
            self.fields['encomiendas'].queryset = Encomienda.objects.filter(pk=encomienda.pk)
            self.fields['encomiendas'].initial = [encomienda]
        elif cliente_cedula:
            # Encomiendas del cliente sin facturar
            self.fields['encomiendas'].queryset = Encomienda.objects.filter(
                remitente__cedula=cliente_cedula,
                estado__in=['registrado', 'en_transito', 'en_destino', 'entregado']
            ).exclude(
                detalles_factura__factura__estado='emitida'
            ).select_related('viaje')
        
        for field_name, field in self.fields.items():
            if field_name not in ['pasajes', 'encomiendas'] and 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-select' if isinstance(
                    field, forms.ModelChoiceField
                ) else 'form-control'
    
    def clean(self):
        cleaned_data = super().clean()
        pasajes = cleaned_data.get('pasajes', [])
        encomiendas = cleaned_data.get('encomiendas', [])
        
        if not pasajes and not encomiendas:
            raise ValidationError(
                "Debe seleccionar al menos un pasaje o encomienda para facturar."
            )
        
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
    
    revertir_caja = forms.BooleanField(
        label="¿Revertir movimiento de caja?",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Crea un movimiento de egreso para revertir el ingreso original."
    )


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

    def __init__(self, *args, **kwargs):
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
