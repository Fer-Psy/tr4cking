"""
Forms for itineraries app.
"""
from django import forms
from django.urls import reverse
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML, Div, Field

from .models import Itinerario, DetalleItinerario, Precio, Horario
from fleet.models import Parada


class ItinerarioForm(forms.ModelForm):
    """Formulario para crear/editar itinerarios."""
    
    class Meta:
        model = Itinerario
        fields = ['empresa', 'nombre', 'ruta', 'distancia_total_km', 'duracion_estimada_hs', 'dias_semana', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Asunción - CDE (Directo)'}),
            'ruta': forms.TextInput(attrs={'placeholder': 'Ej: PY02'}),
            'distancia_total_km': forms.NumberInput(attrs={'placeholder': 'Ej: 327.5', 'step': '0.01'}),
            'duracion_estimada_hs': forms.NumberInput(attrs={'placeholder': 'Ej: 5.5', 'step': '0.01'}),
            'dias_semana': forms.TextInput(attrs={'placeholder': '1111100', 'maxlength': 7}),
        }
        help_texts = {
            'dias_semana': 'Patrón de 7 dígitos: 1=opera, 0=no opera. Ej: 1111100 = Lunes a Viernes',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                'Información del Itinerario',
                Row(
                    Column('nombre', css_class='col-md-8'),
                    Column('ruta', css_class='col-md-4'),
                ),
            ),
            Fieldset(
                'Distancia y Duración',
                Row(
                    Column('distancia_total_km', css_class='col-md-6'),
                    Column('duracion_estimada_hs', css_class='col-md-6'),
                ),
            ),
            Fieldset(
                'Operación',
                Row(
                    Column('dias_semana', css_class='col-md-8'),
                    Column(
                        Div('activo', css_class='form-check form-switch mt-4'),
                        css_class='col-md-4'
                    ),
                ),
            ),
        )
    
    def clean_dias_semana(self):
        dias = self.cleaned_data['dias_semana']
        if len(dias) != 7:
            raise forms.ValidationError("Debe tener exactamente 7 caracteres.")
        if not all(c in '01' for c in dias):
            raise forms.ValidationError("Solo puede contener 0 y 1.")
        return dias


class DetalleItinerarioForm(forms.ModelForm):
    """Formulario para agregar/editar paradas de un itinerario."""
    
    class Meta:
        model = DetalleItinerario
        fields = ['parada', 'orden', 'minutos_desde_origen', 'distancia_desde_origen_km']
        widgets = {
            'orden': forms.NumberInput(attrs={'min': 1, 'placeholder': 'Ej: 1'}),
            'minutos_desde_origen': forms.NumberInput(attrs={'min': 0, 'placeholder': 'Ej: 0'}),
            'distancia_desde_origen_km': forms.NumberInput(attrs={'min': 0, 'step': '0.01', 'placeholder': 'Ej: 45.5'}),
        }
    
    def __init__(self, *args, itinerario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.itinerario = itinerario
        
        # Mejorar las etiquetas de las paradas en el selector
        self.fields['parada'].queryset = Parada.objects.all().select_related('localidad').order_by('localidad__nombre', 'nombre')
        self.fields['parada'].label_from_instance = lambda obj: f"{obj.localidad.nombre}: {obj.nombre}"
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column(
                    Div(
                        Field('parada', wrapper_class='flex-grow-1 mb-0'),
                        HTML('<button type="button" class="btn btn-outline-primary btn-icon ms-2" style="margin-top: 28px;" data-bs-toggle="modal" data-bs-target="#modalParada" title="Nueva Parada"><i class="bi bi-plus-lg"></i></button>'),
                        css_class='d-flex align-items-start'
                    ),
                    css_class='col-md-6'
                ),
                Column('orden', css_class='col-md-6'),
            ),
            Row(
                Column('minutos_desde_origen', css_class='col-md-6'),
                Column('distancia_desde_origen_km', css_class='col-md-6'),
            ),
        )
    
    def clean_orden(self):
        orden = self.cleaned_data['orden']
        if self.itinerario:
            existing = DetalleItinerario.objects.filter(itinerario=self.itinerario, orden=orden)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(f"Ya existe una parada con el orden {orden}.")
        return orden


class HorarioForm(forms.ModelForm):
    """Formulario para crear/editar horarios de salida."""
    
    class Meta:
        model = Horario
        fields = ['itinerario', 'hora_salida', 'activo']
        widgets = {
            'hora_salida': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, itinerario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.itinerario_fijo = itinerario
        
        if self.itinerario_fijo:
            self.fields['itinerario'].initial = self.itinerario_fijo
            # Si se le pasa un itinerario fijo, lo ocultamos
            self.fields['itinerario'].widget = forms.HiddenInput()
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        
        # Layout dinámico
        layout_elements = []
        if self.itinerario_fijo:
            # Si es fijo, todavía necesitamos renderizar el campo oculto
            layout_elements.append('itinerario')
        else:
            layout_elements.append(Row(Column('itinerario', css_class='col-md-12')))
            
        layout_elements.append(
            Row(
                Column('hora_salida', css_class='col-md-8'),
                Column(
                    Div('activo', css_class='form-check form-switch mt-4'),
                    css_class='col-md-4'
                ),
            )
        )
        self.helper.layout = Layout(*layout_elements)
    
    def clean(self):
        cleaned_data = super().clean()
        itinerario = self.itinerario_fijo or cleaned_data.get('itinerario')
        hora = cleaned_data.get('hora_salida')
        
        if itinerario and hora:
            existing = Horario.objects.filter(itinerario=itinerario, hora_salida=hora)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(f"Ya existe un horario a las {hora.strftime('%H:%M')} en {itinerario.nombre}.")
        
        # Si se pasó itinerario fijo, forzar que los datos limpios lo tengan
        if self.itinerario_fijo:
            cleaned_data['itinerario'] = self.itinerario_fijo
            
        return cleaned_data


class PrecioForm(forms.ModelForm):
    """Formulario para crear/editar precios."""
    
    class Meta:
        model = Precio
        fields = ['itinerario', 'origen', 'destino', 'precio']
        widgets = {
            'precio': forms.NumberInput(attrs={'min': 0, 'step': '100', 'placeholder': 'Ej: 85000'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column(
                    Div(
                        Field('itinerario', wrapper_class='flex-grow-1 mb-0'),
                        HTML('<button type="button" class="btn btn-outline-primary btn-icon ms-2" style="margin-top: 28px;" hx-get="' + reverse('itineraries:itinerario_create') + '" hx-target="#modal-itinerario .modal-content" data-bs-toggle="modal" data-bs-target="#modal-itinerario" title="Nuevo Itinerario"><i class="bi bi-plus-lg"></i></button>'),
                        css_class='d-flex align-items-start'
                    ),
                    css_class='col-md-12'
                ),
            ),
            Row(
                Column('origen', css_class='col-md-6'),
                Column('destino', css_class='col-md-6'),
            ),
            'precio',
            HTML('''
                <div class="form-text mb-3">
                    <i class="bi bi-info-circle me-1"></i>
                    El precio se expresa en Guaraníes (Gs.)
                </div>
            '''),
        )
    
    def clean(self):
        cleaned_data = super().clean()
        origen = cleaned_data.get('origen')
        destino = cleaned_data.get('destino')
        
        if origen and destino and origen == destino:
            raise forms.ValidationError("El origen y destino no pueden ser iguales.")
        
        return cleaned_data
