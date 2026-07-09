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
        label='Cuenta de Usuario Existente',
        help_text='Opcional. Vincula esta persona con una cuenta ya existente.',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Campos para creación/gestión rápida desde admin
    username = forms.CharField(
        required=False,
        label='Nuevo Nombre de Usuario',
        widget=forms.TextInput(attrs={'placeholder': 'Ej: juan.perez', 'class': 'form-control'})
    )
    password = forms.CharField(
        required=False,
        label='Nueva Contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Dejar en blanco para no cambiar', 'class': 'form-control'})
    )

    
    class Meta:
        model = Persona
        fields = [
            'cedula', 'nombre', 'apellido', 'telefono', 'email', 
            'direccion', 'latitud', 'longitud', 'empresa', 'es_chofer', 'es_ayudante', 'es_cliente', 'es_agente', 'user'
        ]
        widgets = {
            'cedula': forms.TextInput(attrs={'placeholder': 'Ej: 1234567 o 1234567-8'}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre'}),
            'apellido': forms.TextInput(attrs={'placeholder': 'Apellido'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Ej: 0981 123 456'}),
            'email': forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
            'direccion': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Dirección completa'}),
            'latitud': forms.TextInput(attrs={'placeholder': 'Latitud', 'readonly': 'readonly'}),
            'longitud': forms.TextInput(attrs={'placeholder': 'Longitud', 'readonly': 'readonly'}),
        }
    
    def __init__(self, *args, user_is_admin=False, user_is_agente=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_is_admin = user_is_admin
        self.user_is_agente = user_is_agente
        
        # Ocultar roles administrativos si no es admin
        if not self.user_is_admin:
            # Los roles se ocultan del formulario
            for field in ['es_chofer', 'es_ayudante', 'es_agente', 'empresa']:
                if field in self.fields:
                    self.fields[field].disabled = True
                    self.fields[field].required = False
                    
        # Para el Agente, forzar que solo pueda ver/crear cliente
        if self.user_is_agente and 'es_cliente' in self.fields:
            self.fields['es_cliente'].initial = True
            self.fields['es_cliente'].disabled = True

        # Mostrar usuarios con formato legible y ordenados
        self.fields['user'].queryset = User.objects.all().order_by('username')
        self.fields['user'].label_from_instance = lambda obj: f"{obj.username} ({obj.get_full_name() or obj.email or 'Sin nombre'})"
        
        # Agregar opción vacía
        self.fields['user'].empty_label = "-- Sin usuario vinculado --"
        
        self.helper = FormHelper()
        self.helper.form_tag = False
        
        # Construir el layout dinámicamente según permisos
        roles_layout = [
            Column(Div('es_cliente', css_class='form-check form-switch'), css_class='col-md-12'),
        ]
        
        if self.user_is_admin:
            roles_layout_admin = [
                Row(
                    Column(Div('es_chofer', css_class='form-check form-switch'), css_class='col-md-4'),
                    Column(Div('es_ayudante', css_class='form-check form-switch'), css_class='col-md-4'),
                    Column(Div('es_agente', css_class='form-check form-switch'), css_class='col-md-4'),
                )
            ]
        else:
            roles_layout_admin = [HTML('<div class="alert alert-info py-2 small mb-0"><i class="bi bi-lock me-1"></i> Solo administradores pueden gestionar roles internos.</div>')]

        self.helper.layout = Layout(
            Fieldset(
                'Información Personal',
                Row(
                    Column('cedula', css_class='col-md-4'),
                    Column('nombre', css_class='col-md-4'),
                    Column('apellido', css_class='col-md-4'),
                ),
                Row(
                    Column('telefono', css_class='col-md-4'),
                    Column('email', css_class='col-md-4'),
                    Column('empresa' if self.user_is_admin else HTML(''), css_class='col-md-4'),
                ),
                'direccion',
                Row(
                    Column('latitud', css_class='col-md-6'),
                    Column('longitud', css_class='col-md-6'),
                ),
            ),
            Fieldset(
                'Roles del Sistema',
                Row(*roles_layout),
                HTML('<div class="mt-2"></div>'),
                *roles_layout_admin,
            ),
            Fieldset(
                'Cuenta de Usuario',
                Row(
                    Column('username', css_class='col-md-6'),
                    Column('password', css_class='col-md-6'),
                ) if self.user_is_admin else HTML('<p class="text-muted">La vinculación de cuentas está restringida a administradores.</p>'),
                HTML('<div class="alert alert-warning py-1 small mt-2"><i class="bi bi-info-circle me-1"></i> Ingresa un nombre de usuario y contraseña para crear la cuenta de acceso al sistema.</div>') if self.user_is_admin else HTML(''),
            ),
        )

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if cedula and str(cedula).strip().startswith('-'):
            raise forms.ValidationError("El campo Cédula/RUC no puede ser negativo.")
            
        if cedula:
            qs = Persona.objects.filter(cedula=cedula)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Esta Cédula/RUC ya está registrada en el sistema.")
                
        return cedula

    def clean_username(self):
        username = self.cleaned_data.get('username')
        user_existente = self.cleaned_data.get('user')
        
        if username:
            # Si estoy creando/actualizando con un username, verificar disponibilidad
            query = User.objects.filter(username=username)
            if self.instance.pk and self.instance.user:
                query = query.exclude(pk=self.instance.user.pk)
            
            if query.exists():
                raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        username = self.cleaned_data.get('username')
        if password and len(password) < 6:
            raise forms.ValidationError("La contraseña debe tener al menos 6 caracteres.")
        if username and not self.instance.user and not password:
            raise forms.ValidationError("Debes asignar una contraseña para el nuevo usuario.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        roles = [
            cleaned_data.get('es_chofer', False),
            cleaned_data.get('es_ayudante', False),
            cleaned_data.get('es_cliente', False),
            cleaned_data.get('es_agente', False)
        ]
        if sum(bool(role) for role in roles) > 1:
            raise forms.ValidationError("Una persona solo puede tener un único rol en el sistema.")
        return cleaned_data

    def save(self, commit=True):
        persona = super().save(commit=False)
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        linked_user = self.cleaned_data.get('user')

        if self.user_is_agente:
            persona.es_cliente = True
            persona.es_chofer = False
            persona.es_ayudante = False
            persona.es_agente = False

        if self.user_is_admin:
            original_user = None
            if persona.pk:
                original_user = Persona.objects.get(pk=persona.pk).user

            if username:
                # Crear o actualizar usuario
                if original_user:
                    user = original_user
                    user.username = username
                    if password:
                        user.set_password(password)
                    user.save()
                    persona.user = user
                else:
                    user = User.objects.create_user(
                        username=username,
                        password=password or 'cambiar123',
                        email=self.cleaned_data.get('email', '')
                    )
                    persona.user = user
                
                # Sincronizar datos básicos
                user.first_name = self.cleaned_data.get('nombre', '')
                user.last_name = self.cleaned_data.get('apellido', '')
                user.save()
            elif linked_user:
                persona.user = linked_user
                # Opcional: Actualizar contraseña si se proveyó una
                if password:
                    linked_user.set_password(password)
                    linked_user.save()

        if commit:
            persona.save()
        return persona



class LocalidadForm(forms.ModelForm):
    """Formulario para crear/editar localidades."""
    
    class Meta:
        model = Localidad
        fields = ['nombre', 'latitud', 'longitud']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej: Asunción',
                'class': 'form-control',
            }),
            'latitud': forms.TextInput(attrs={
                'placeholder': 'Ej: -25.2867',
                'class': 'form-control',
                'readonly': 'readonly',
            }),
            'longitud': forms.TextInput(attrs={
                'placeholder': 'Ej: -57.3333',
                'class': 'form-control',
                'readonly': 'readonly',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Desactivar localización para que use punto decimal, no coma
        self.fields['latitud'].localize = False
        self.fields['longitud'].localize = False
        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre:
            # Check for existing locality with same name (ignoring case)
            existe = Localidad.objects.filter(nombre__iexact=nombre)
            if self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)
            if existe.exists():
                raise forms.ValidationError(f"La localidad '{nombre}' ya existe en el sistema.")
        return nombre


class ClienteRegistroForm(forms.ModelForm):
    """Formulario para registro público de nuevos clientes."""
    
    username = forms.CharField(label="Nombre de Usuario", widget=forms.TextInput(attrs={'placeholder': 'Ej: juanperez'}))
    password = forms.CharField(label="Contraseña", help_text="La contraseña debe tener al menos 6 caracteres.", widget=forms.PasswordInput(attrs={'placeholder': '********'}))
    password_confirm = forms.CharField(label="Confirmar Contraseña", widget=forms.PasswordInput(attrs={'placeholder': '********'}))
    
    class Meta:
        model = Persona
        fields = ['cedula', 'nombre', 'apellido', 'telefono', 'email', 'direccion']
        widgets = {
            'cedula': forms.TextInput(attrs={'placeholder': 'Ej: 1234567-8'}),
            'direccion': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Para entrega de encomiendas'}),
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                'Datos de Acceso',
                'username',
                Row(
                    Column('password', css_class='col-md-6'),
                    Column('password_confirm', css_class='col-md-6'),
                ),
            ),
            Fieldset(
                'Datos Personales',
                Row(
                    Column('cedula', css_class='col-md-12'),
                ),
                Row(
                    Column('nombre', css_class='col-md-6'),
                    Column('apellido', css_class='col-md-6'),
                ),
                Row(
                    Column('telefono', css_class='col-md-6'),
                    Column('email', css_class='col-md-6'),
                ),
                'direccion',
                Row(
                    Column('latitud', css_class='col-md-6'),
                    Column('longitud', css_class='col-md-6'),
                ),
            ),
        )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 6:
            raise forms.ValidationError("La contraseña debe tener al menos 6 caracteres.")
        return password
    
    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if cedula and str(cedula).strip().startswith('-'):
            raise forms.ValidationError("El campo Cédula/RUC no puede ser negativo.")
        if Persona.objects.filter(cedula=cedula).exists():
            raise forms.ValidationError("Esta cédula ya está registrada en el sistema.")
        return cedula

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data
    
    def save(self, commit=True):
        # Primero crear el usuario de Django
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            password=self.cleaned_data['password'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['nombre'],
            last_name=self.cleaned_data['apellido']
        )
        
        # Luego crear la Persona vinculada
        persona = super().save(commit=False)
        persona.user = user
        persona.es_cliente = True
        
        if commit:
            persona.save()
        return persona


class ClientePerfilForm(forms.ModelForm):
    """Formulario para que el cliente edite su propio perfil."""
    
    username = forms.CharField(
        label="Nombre de Usuario", 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label="Nueva Contraseña", 
        required=False,
        help_text="Dejar en blanco para mantener la actual.",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'})
    )
    password_confirm = forms.CharField(
        label="Confirmar Nueva Contraseña", 
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'})
    )
    
    class Meta:
        model = Persona
        fields = ['cedula', 'nombre', 'apellido', 'telefono', 'email', 'direccion', 'latitud', 'longitud']
        widgets = {
            'cedula': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'direccion': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'latitud': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'longitud': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['username'].initial = self.instance.user.username
            
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                'Datos de Acceso',
                'username',
                Row(
                    Column('password', css_class='col-md-6'),
                    Column('password_confirm', css_class='col-md-6'),
                ),
            ),
            Fieldset(
                'Datos Personales',
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
                Row(
                    Column('latitud', css_class='col-md-6'),
                    Column('longitud', css_class='col-md-6'),
                ),
            ),
        )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.user.pk).exists():
            raise forms.ValidationError("Este nombre de usuario ya está en uso.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if password and len(password) < 6:
            raise forms.ValidationError("La contraseña debe tener al menos 6 caracteres.")
        return password
    
    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if cedula and str(cedula).strip().startswith('-'):
            raise forms.ValidationError("El campo Cédula/RUC no puede ser negativo.")
        return cedula

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas nuevas no coinciden.")
        return cleaned_data
    
    def save(self, commit=True):
        persona = super().save(commit=False)
        user = persona.user
        
        # Actualizar datos del usuario de Django
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data.get('email') or ''
        user.first_name = self.cleaned_data['nombre']
        user.last_name = self.cleaned_data['apellido']
        
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        
        user.save()
        
        if commit:
            persona.save()
        return persona
