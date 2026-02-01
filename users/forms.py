"""
Forms for users app.
"""
from django import forms
from django.contrib.auth.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML, Div

from .models import Persona, Localidad


class PersonaForm(forms.ModelForm):
    """Formulario para crear/editar personas."""
    
    # Campo opcional para relacionar con un usuario del sistema
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label='Cuenta de Usuario',
        help_text='Opcional. Vincula esta persona con una cuenta de usuario del sistema.',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = Persona
        fields = [
            'cedula', 'nombre', 'apellido', 'telefono', 'email', 
            'direccion', 'es_empleado', 'es_cliente', 'es_pasajero', 'user'
        ]
        widgets = {
            'cedula': forms.NumberInput(attrs={'placeholder': 'Ej: 4567890'}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre'}),
            'apellido': forms.TextInput(attrs={'placeholder': 'Apellido'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Ej: 0981 123 456'}),
            'email': forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
            'direccion': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Dirección completa'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mostrar usuarios con formato legible y ordenados
        self.fields['user'].queryset = User.objects.all().order_by('username')
        self.fields['user'].label_from_instance = lambda obj: f"{obj.username} ({obj.get_full_name() or obj.email or 'Sin nombre'})"
        
        # Agregar opción vacía
        self.fields['user'].empty_label = "-- Sin usuario vinculado --"
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                'Información Personal',
                Row(
                    Column('cedula', css_class='col-md-4'),
                    Column('nombre', css_class='col-md-4'),
                    Column('apellido', css_class='col-md-4'),
                ),
                Row(
                    Column('telefono', css_class='col-md-6'),
                    Column('email', css_class='col-md-6'),
                ),
                'direccion',
            ),
            Fieldset(
                'Roles',
                Row(
                    Column(
                        Div('es_empleado', css_class='form-check form-switch'),
                        css_class='col-md-4'
                    ),
                    Column(
                        Div('es_cliente', css_class='form-check form-switch'),
                        css_class='col-md-4'
                    ),
                    Column(
                        Div('es_pasajero', css_class='form-check form-switch'),
                        css_class='col-md-4'
                    ),
                ),
            ),
            Fieldset(
                'Cuenta de Usuario',
                'user',
                HTML('''
                    <div class="form-text mb-3">
                        <i class="bi bi-info-circle me-1"></i>
                        Si la persona es un empleado que necesita acceder al sistema, 
                        puedes vincularla con una cuenta de usuario existente o crear una desde el 
                        <a href="/admin/auth/user/add/" target="_blank">panel de administración</a>.
                    </div>
                '''),
            ),
        )


class LocalidadForm(forms.ModelForm):
    """Formulario para crear/editar localidades."""
    
    class Meta:
        model = Localidad
        fields = ['nombre', 'latitud', 'longitud']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Asunción'}),
            'latitud': forms.NumberInput(attrs={'placeholder': 'Ej: -25.2867', 'step': '0.000001'}),
            'longitud': forms.NumberInput(attrs={'placeholder': 'Ej: -57.3333', 'step': '0.000001'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'nombre',
            Row(
                Column('latitud', css_class='col-md-6'),
                Column('longitud', css_class='col-md-6'),
            ),
            HTML('''
                <div class="form-text mb-3">
                    <i class="bi bi-info-circle me-1"></i>
                    Las coordenadas son opcionales. Puedes obtenerlas desde Google Maps.
                </div>
            '''),
        )
