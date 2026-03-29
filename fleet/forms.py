"""
Forms for fleet app.
"""
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML, Div, Field

from .models import Empresa, Parada, Bus, Asiento
from users.models import Localidad


class EmpresaForm(forms.ModelForm):
    """Formulario para crear/editar empresas."""
    
    class Meta:
        model = Empresa
        fields = ['nombre', 'ruc', 'telefono', 'email', 'direccion_legal']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre de la empresa'}),
            'ruc': forms.TextInput(attrs={'placeholder': 'Ej: 80012345-6'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Ej: 021 123 456'}),
            'email': forms.EmailInput(attrs={'placeholder': 'contacto@empresa.com'}),
            'direccion_legal': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Dirección legal completa'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                'Información de la Empresa',
                Row(
                    Column('nombre', css_class='col-md-8'),
                    Column('ruc', css_class='col-md-4'),
                ),
                Row(
                    Column('telefono', css_class='col-md-6'),
                    Column('email', css_class='col-md-6'),
                ),
                'direccion_legal',
            ),
        )


class ParadaForm(forms.ModelForm):
    """Formulario para crear/editar paradas."""
    
    class Meta:
        model = Parada
        fields = ['empresa', 'localidad', 'nombre', 'direccion', 'latitud_gps', 'longitud_gps', 'es_agencia']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Terminal de Asunción'}),
            'direccion': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Dirección de la parada'}),
            'latitud_gps': forms.NumberInput(attrs={'placeholder': 'Ej: -25.2867', 'step': '0.000001'}),
            'longitud_gps': forms.NumberInput(attrs={'placeholder': 'Ej: -57.3333', 'step': '0.000001'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['localidad'].queryset = Localidad.objects.all().order_by('nombre')
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                'Información de la Parada',
                Row(
                    Column('empresa', css_class='col-md-6'),
                    Column(
                        Div(
                            Field('localidad', wrapper_class='flex-grow-1 mb-0'),
                            HTML('<button type="button" class="btn btn-outline-primary btn-icon ms-2" style="margin-top: 28px;" data-bs-toggle="modal" data-bs-target="#modalLocalidad" title="Nueva Localidad"><i class="bi bi-plus-lg"></i></button>'),
                            css_class='d-flex align-items-start'
                        ),
                        css_class='col-md-6'
                    ),
                ),
                'nombre',
                'direccion',
            ),
            Fieldset(
                'Ubicación GPS',
                Row(
                    Column('latitud_gps', css_class='col-md-6'),
                    Column('longitud_gps', css_class='col-md-6'),
                ),
            ),
            Fieldset(
                'Opciones',
                Div('es_agencia', css_class='form-check form-switch'),
            ),
        )

    def clean(self):
        cleaned_data = super().clean()
        empresa = cleaned_data.get('empresa')
        localidad = cleaned_data.get('localidad')
        nombre = cleaned_data.get('nombre')
        
        if empresa and localidad and nombre:
            # Check for existing parada with same name in same locality for same company
            existe = Parada.objects.filter(
                empresa=empresa, 
                localidad=localidad, 
                nombre__iexact=nombre
            )
            if self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)
            
            if existe.exists():
                raise forms.ValidationError(
                    f"Ya existe una parada llamada '{nombre}' registrada para la empresa '{empresa}' "
                    f"en '{localidad}'."
                )
        return cleaned_data


class BusForm(forms.ModelForm):
    """Formulario para crear/editar buses."""
    
    # Campo extra para tipo de asiento (no pertenece al modelo Bus)
    tipo_asiento = forms.ChoiceField(
        choices=Asiento.TIPO_ASIENTO_CHOICES,
        initial='convencional',
        required=True,
        label='Tipo de asiento',
        help_text='Tipo de asiento que se asignará a todos los asientos generados automáticamente.',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    
    # Campo para regenerar asientos (solo para edición)
    regenerar_asientos = forms.BooleanField(
        required=False,
        label='Regenerar todos los asientos',
        help_text='Si se marca, se eliminarán los asientos actuales y se volverán a generar según la nueva capacidad y tipo.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    
    class Meta:
        model = Bus
        fields = ['empresa', 'placa', 'marca', 'modelo', 'capacidad_pisos', 'capacidad_asientos', 'estado']
        widgets = {
            'placa': forms.TextInput(attrs={'placeholder': 'Ej: ABC-123'}),
            'marca': forms.TextInput(attrs={'placeholder': 'Ej: Mercedes-Benz'}),
            'modelo': forms.TextInput(attrs={'placeholder': 'Ej: O500 RSD'}),
            'capacidad_pisos': forms.NumberInput(attrs={'min': 1, 'max': 2}),
            'capacidad_asientos': forms.NumberInput(attrs={'min': 1, 'placeholder': 'Ej: 44'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        
        # Si es edición, mostramos el campo para regenerar
        mostrar_regenerar = self.instance.pk is not None
        
        self.helper.layout = Layout(
            Fieldset(
                'Información del Bus',
                Row(
                    Column('empresa', css_class='col-md-6'),
                    Column('placa', css_class='col-md-6'),
                ),
                Row(
                    Column('marca', css_class='col-md-6'),
                    Column('modelo', css_class='col-md-6'),
                ),
            ),
            Fieldset(
                'Capacidad y Estado',
                Row(
                    Column('capacidad_pisos', css_class='col-md-4'),
                    Column('capacidad_asientos', css_class='col-md-4'),
                    Column('estado', css_class='col-md-4'),
                ),
            ),
            Fieldset(
                'Configuración de Asientos',
                Row(
                    Column('tipo_asiento', css_class='col-md-6'),
                ),
                Div(
                    'regenerar_asientos',
                    css_class='form-check mb-3' if mostrar_regenerar else 'd-none'
                ),
                HTML(f'''
                    <div class="alert alert-info mt-2" style="font-size: 0.85rem;">
                        <div class="d-flex align-items-start">
                            <i class="bi bi-info-circle me-2 mt-1"></i>
                            <div>
                                <strong>Generación automática:</strong> {'Al guardar,' if mostrar_regenerar else 'Al crear el bus,'} se generarán 
                                automáticamente todos los asientos con el tipo seleccionado, numerados del 1 al 
                                total de la capacidad indicada.
                                { '<br><span class="text-danger"><strong>Atención:</strong> Si marca "Regenerar", se perderán los cambios manuales hechos a los asientos actuales.</span>' if mostrar_regenerar else '' }
                            </div>
                        </div>
                    </div>
                '''),
            ),
        )


class AsientoForm(forms.ModelForm):
    """Formulario para crear/editar asientos."""
    
    class Meta:
        model = Asiento
        fields = ['numero_asiento', 'piso', 'tipo_asiento']
        widgets = {
            'numero_asiento': forms.NumberInput(attrs={'min': 1, 'placeholder': 'Ej: 1'}),
            'piso': forms.NumberInput(attrs={'min': 1, 'max': 2}),
        }
    
    def __init__(self, *args, bus=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.bus = bus
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('numero_asiento', css_class='col-md-4'),
                Column('piso', css_class='col-md-4'),
                Column('tipo_asiento', css_class='col-md-4'),
            ),
        )
    
    def clean_numero_asiento(self):
        numero = self.cleaned_data['numero_asiento']
        if self.bus:
            existing = Asiento.objects.filter(bus=self.bus, numero_asiento=numero)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(f"Ya existe el asiento {numero} en este bus.")
        return numero
