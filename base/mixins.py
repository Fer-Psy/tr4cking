from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

class AdminOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin para requerir que el usuario sea administrador (staff o superuser)
    o que al menos no tenga roles operativos/comerciales restringidos 
    (como Agente, Chofer o Ayudante).
    """
    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
            
        if user.is_superuser or user.is_staff:
            return True
            
        persona = getattr(user, 'persona', None)
        if persona:
            # Los agentes comerciales, choferes y ayudantes NO tienen acceso a estas configuraciones
            if persona.es_agente or persona.es_chofer or persona.es_ayudante:
                return False
                
        # Por defecto, si es un usuario común sin rol restringido, podríamos dejarlo, 
        # o podríamos restringir solo a admin explícito. 
        # Como no todos los clientes usan is_staff, limitamos bloqueando explícitamente los operativos
        return True
