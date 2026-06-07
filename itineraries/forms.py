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
    
    DIAS_CHOICES = [
        ('0', 'Lunes'),
        ('1', 'Martes'),
        ('2', 'Miércoles'),
        ('3', 'Jueves'),
        ('4', 'Viernes'),
        ('5', 'Sábado'),
        ('6', 'Domingo'),
    ]
    
    dias_semana_checkboxes = forms.MultipleChoiceField(
        choices=DIAS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        label="Días de la semana",
        required=True,
    )
    
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
            'dias_semana': forms.HiddenInput(),
            'horarios': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mejorar visualización de paradas
        paradas_qs = Parada.objects.all().select_related('localidad', 'empresa').order_by('localidad__nombre', 'nombre')
        
        # Configurar atributos HTMX para filtrar la parada de origen al cambiar la empresa
        from django.urls import reverse
        self.fields['empresa'].widget.attrs.update({
            'hx-get': reverse('itineraries:obtener_paradas_empresa'),
            'hx-target': '#id_parada_origen',
            'hx-trigger': 'change',
        })

        # Hacer que dias_semana no sea requerido en el formulario porque se calcula en clean_dias_semana
        self.fields['dias_semana'].required = False

        # Obtener la empresa seleccionada (de POST o de la instancia) para filtrar inicialmente
        empresa_id = None
        if self.is_bound and self.data and hasattr(self.data, 'get') and self.data.get('empresa'):
            empresa_id = self.data.get('empresa')
        elif self.instance and self.instance.empresa_id:
            empresa_id = self.instance.empresa_id
            
        if empresa_id:
            try:
                paradas_qs = paradas_qs.filter(empresa_id=int(empresa_id))
            except (ValueError, TypeError):
                pass
                
        self.fields['parada_origen'].queryset = paradas_qs
        self.fields['parada_origen'].label_from_instance = lambda obj: f"{obj.localidad.nombre}: {obj.nombre} ({obj.empresa.nombre})"

        # Cargar parada de origen inicial si existe instancia y tiene primera parada
        if self.instance and self.instance.pk:
            primera = self.instance.primera_parada
            if primera:
                self.fields['parada_origen'].initial = primera.parada

        # Cargar los días de la semana iniciales si existe instancia
        if self.instance and self.instance.pk and self.instance.dias_semana:
            dias_activos = []
            for i, char in enumerate(self.instance.dias_semana):
                if char == '1':
                    dias_activos.append(str(i))
            self.fields['dias_semana_checkboxes'].initial = dias_activos

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
                    Column(
                        Field('dias_semana_checkboxes', wrapper_class='d-flex flex-wrap gap-3'),
                        css_class='col-md-8'
                    ),
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
        # Use self.data instead of self.cleaned_data because dias_semana_checkboxes
        # (a declared field) is cleaned AFTER dias_semana (a model field in Meta.fields)
        # due to Django's field ordering in ModelForms.
        dias_seleccionados = self.data.getlist('dias_semana_checkboxes', [])
        
        if not dias_seleccionados:
            raise forms.ValidationError("Debe seleccionar al menos un día de la semana.")
            
        bin_list = ['0'] * 7
        for val in dias_seleccionados:
            try:
                idx = int(val)
                if 0 <= idx < 7:
                    bin_list[idx] = '1'
            except (ValueError, TypeError):
                continue
        
        dias = "".join(bin_list)
        return dias

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        empresa = cleaned_data.get('empresa')
        
        if nombre and empresa:
            existing = Itinerario.objects.filter(
                empresa=empresa,
                nombre__iexact=nombre.strip()
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                self.add_error('nombre', f"Ya existe un itinerario con el nombre '{nombre}' para la empresa {empresa.nombre}.")
        return cleaned_data

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
            'origen': forms.HiddenInput(),
            'destino': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
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
