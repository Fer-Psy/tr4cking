"""
Middleware para forzar el cierre diario de caja.

Los usuarios con roles de caja (agente, ayudante) deben cerrar la caja
antes de las 23:00 hs. Si la sesión queda abierta de un día anterior,
o si pasan las 23:00 sin cerrar, el sistema redirige obligatoriamente
al formulario de cierre de caja.
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.conf import settings


class CierreCajaObligatorioMiddleware:
    """
    Middleware que intercepta requests y redirige al cierre de caja
    cuando un usuario con caja tiene una sesión vencida.
    """

    # URLs que están exentas de la redirección (el usuario puede acceder aunque
    # tenga caja pendiente de cierre)
    URLS_EXENTAS = [
        'operations:caja_cerrar',
        'logout',
        'login',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ejecutar la verificación antes de procesar la vista
        redireccion = self._verificar_cierre_caja(request)
        if redireccion:
            return redireccion

        response = self.get_response(request)
        return response

    def _verificar_cierre_caja(self, request):
        """
        Verifica si el usuario debe ser redirigido al cierre de caja.
        Retorna un redirect si debe ser redirigido, o None si puede continuar.
        """
        # No verificar para usuarios no autenticados
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None

        # No verificar para requests AJAX/HTMX (evitar romper llamadas asíncronas)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return None
        if getattr(request, 'htmx', False):
            return None

        # No verificar archivos estáticos ni admin
        path = request.path
        if path.startswith('/static/') or path.startswith('/media/') or path.startswith('/admin/'):
            return None

        # No redirigir si ya está en una URL exenta
        for url_name in self.URLS_EXENTAS:
            try:
                url_exenta = reverse(url_name)
                if path == url_exenta:
                    return None
            except Exception:
                continue

        # Verificar si el usuario tiene un rol con caja
        if not self._usuario_tiene_caja(request.user):
            return None

        # Verificar si tiene sesión de caja vencida
        sesion_vencida = self._obtener_sesion_vencida(request.user)
        if sesion_vencida:
            # Marcar en el request para que las vistas/templates puedan saberlo
            request.caja_pendiente_cierre = True
            request.sesion_caja_vencida = sesion_vencida

            from django.contrib import messages
            messages.warning(
                request,
                "⚠️ Tiene una caja abierta del día anterior que debe cerrar antes de continuar."
            )
            return redirect(f"{reverse('operations:caja_cerrar')}?forzado=1")

        # No hay sesión vencida
        request.caja_pendiente_cierre = False
        return None

    def _usuario_tiene_caja(self, user):
        """
        Determina si un usuario tiene un rol que maneja caja.
        Roles con caja: agente, ayudante.
        Staff/superusers son excluidos.
        """
        if user.is_superuser or user.is_staff:
            return False

        persona = getattr(user, 'persona', None)
        if not persona:
            return False

        return persona.es_agente or persona.es_ayudante

    def _obtener_sesion_vencida(self, user):
        """
        Busca una sesión de caja abierta que haya vencido.
        
        Una sesión está vencida si:
        1. Fue abierta en un día anterior al actual, O
        2. Fue abierta hoy pero ya pasaron las 23:00 hs (hora límite)
        """
        from operations.models import SesionCaja

        try:
            sesion = SesionCaja.objects.filter(
                cajero=user,
                estado='abierta'
            ).order_by('-fecha_apertura').first()

            if not sesion:
                return None

            ahora = timezone.localtime(timezone.now())
            fecha_apertura_local = timezone.localtime(sesion.fecha_apertura)
            hora_limite = getattr(settings, 'CAJA_HORA_LIMITE_CIERRE', 23)

            # Caso 1: Sesión abierta en un día anterior
            if fecha_apertura_local.date() < ahora.date():
                return sesion

            # Caso 2: Sesión abierta hoy pero pasaron las 23:00
            if fecha_apertura_local.date() == ahora.date() and ahora.hour >= hora_limite:
                return sesion

            return None

        except Exception:
            return None
