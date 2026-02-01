"""
Forms for fleet app.
"""
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML, Div

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
        fields = ['empresa', 'localidad', 'nombre', 'direccion', 'latitud_gps', 'longitud_gps', 'es_sucursal']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Terminal de Asunción'}),
            'direccion': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Dirección de la parada'}),
            'latitud_gps': forms.NumberInput(attrs={'placeholder': 'Ej: -25.2867', 'step': '0.000001'}),
            'longitud_gps': forms.NumberInput(attrs={'placeholder': 'Ej: -57.3333', 'step': '0.000001'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                'Información de la Parada',
                Row(
                    Column('empresa', css_class='col-md-6'),
                    Column('localidad', css_class='col-md-6'),
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
                Div('es_sucursal', css_class='form-check form-switch'),
            ),
        )


class BusForm(forms.ModelForm):
    """Formulario para crear/editar buses."""
    
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
                'Capacidad',
                Row(
                    Column('capacidad_pisos', css_class='col-md-4'),
                    Column('capacidad_asientos', css_class='col-md-4'),
                    Column('estado', css_class='col-md-4'),
                ),
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
