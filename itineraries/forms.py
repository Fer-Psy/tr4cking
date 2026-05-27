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
    
    parada_origen = forms.ModelChoiceField(
        queryset=Parada.objects.all(),
        required=False,
        label="Parada de Origen (Opcional)",
        help_text="Se creará automáticamente con Orden 1."
    )

    class Meta:
        model = Itinerario
        fields = [
            'empresa', 'nombre', 'ruta', 'distancia_total_km', 'duracion_estimada_hs', 
            'dias_semana', 'horarios', 'activo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Asunción - CDE (Directo)'}),
            'ruta': forms.TextInput(attrs={'placeholder': 'Ej: PY02'}),
            'distancia_total_km': forms.NumberInput(attrs={'placeholder': 'Ej: 327.5', 'step': '0.01'}),
            'duracion_estimada_hs': forms.NumberInput(attrs={'placeholder': 'Ej: 5.5', 'step': '0.01'}),
            'dias_semana': forms.TextInput(attrs={'placeholder': '1111111', 'maxlength': 7}),
            'horarios': forms.CheckboxSelectMultiple(),
        }
        help_texts = {
            'dias_semana': 'Patrón de 7 dígitos: 1=opera, 0=no opera. Ej: 1111111 = Todos los días',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mejorar visualización de paradas
        paradas_qs = Parada.objects.all().select_related('localidad').order_by('localidad__nombre', 'nombre')
        self.fields['parada_origen'].queryset = paradas_qs
        
        label_func = lambda obj: f"{obj.localidad.nombre}: {obj.nombre}"
        self.fields['parada_origen'].label_from_instance = label_func

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                'Información del Itinerario',
                Row(
                    Column('empresa', css_class='col-md-12'),
                ),
                Row(
                    Column('nombre', css_class='col-md-8'),
                    Column('ruta', css_class='col-md-4'),
                ),
            ),
            Fieldset(
                'Recorrido Inicial (Opcional)',
                Row(
                    Column(
                        Div(
                            Field('parada_origen', wrapper_class='flex-grow-1 mb-0'),
                            HTML('<button type="button" class="btn btn-outline-primary btn-icon ms-2" style="margin-top: 28px;" data-bs-target="#modalParada" title="Nueva Parada"><i class="bi bi-plus-lg"></i></button>'),
                            css_class='d-flex align-items-start'
                        ),
                        css_class='col-md-12'
                    ),
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
                'Operación y Horarios',
                Row(
                    Column('dias_semana', css_class='col-md-8'),
                    Column(
                        Div('activo', css_class='form-check form-switch mt-4'),
                        css_class='col-md-4'
                    ),
                ),
                Row(
                    Column(
                        Div(
                            HTML('<label class="form-label fw-semibold">Horarios de salida</label>'),
                             HTML('<button type="button" class="btn btn-outline-primary btn-sm btn-icon ms-2" data-bs-target="#modalHorario" title="Nuevo Horario"><i class="bi bi-plus-lg"></i></button>'),
                            css_class='d-flex align-items-center'
                        ),
                        Field('horarios', label_class='d-none', css_id='id_horarios_container'),
                        css_class='col-md-12 mt-2'
                    )
                )
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
        paradas_qs = Parada.objects.all().select_related('localidad').order_by('localidad__nombre', 'nombre')
        
        # Filtrar paradas por la empresa del itinerario si está disponible
        if self.itinerario and self.itinerario.empresa:
            paradas_qs = paradas_qs.filter(empresa=self.itinerario.empresa)
            
        self.fields['parada'].queryset = paradas_qs
        self.fields['parada'].label_from_instance = lambda obj: f"{obj.localidad.nombre}: {obj.nombre}"
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column(
                    Div(
                        Field('parada', wrapper_class='flex-grow-1 mb-0'),
                        HTML('<button type="button" class="btn btn-outline-primary btn-icon ms-2" style="margin-top: 28px;" data-bs-target="#modalParada" title="Nueva Parada"><i class="bi bi-plus-lg"></i></button>'),
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
        fields = ['hora_salida', 'activo']
        widgets = {
            'hora_salida': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        
        # Layout dinámico
        layout_elements = [
            Row(
                Column('hora_salida', css_class='col-md-8'),
                Column(
                    Div('activo', css_class='form-check form-switch mt-4'),
                    css_class='col-md-4'
                ),
            )
        ]
        self.helper.layout = Layout(*layout_elements)
    
    def clean(self):
        cleaned_data = super().clean()
        hora = cleaned_data.get('hora_salida')
        
        if hora:
            existing = Horario.objects.filter(hora_salida=hora)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError(f"Ya existe el horario de las {hora.strftime('%H:%M')}.")
            
        return cleaned_data


class PrecioForm(forms.ModelForm):
    """Formulario para crear/editar precios."""
    
    class Meta:
        model = Precio
        fields = ['origen', 'destino', 'precio']
        widgets = {
            'precio': forms.NumberInput(attrs={'min': 0, 'step': '100', 'placeholder': 'Ej: 85000'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
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

class ItinerarioAddHorarioForm(forms.Form):
    """Formulario para seleccionar horarios existentes y agregarlos al itinerario."""
    horarios = forms.ModelMultipleChoiceField(
        queryset=Horario.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Horarios Disponibles",
        help_text="Seleccione uno o más horarios para agregar al itinerario."
    )
    
    def __init__(self, *args, itinerario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.itinerario = itinerario
        
        if self.itinerario:
            self.fields['horarios'].queryset = Horario.objects.exclude(
                id__in=self.itinerario.horarios.values_list('id', flat=True)
            ).order_by('hora_salida')
            
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'horarios'
        )
