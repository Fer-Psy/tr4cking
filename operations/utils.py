"""
Utilidades para gestión de asientos por segmento.
Lógica core del sistema de ocupación de asientos.
"""
from django.db.models import Q


def asiento_disponible_en_tramo(viaje, asiento, orden_origen, orden_destino):
    """
    Verifica si un asiento está disponible para un tramo específico del viaje.
    
    Un asiento está OCUPADO si existe un pasaje activo cuyo rango
    [orden_origen, orden_destino) se solapa con el tramo consultado.
    
    Dos rangos [A, B) y [C, D) se solapan si A < D AND C < B.
    
    Args:
        viaje: Instancia de Viaje
        asiento: Instancia de Asiento
        orden_origen: Int, orden de la parada donde sube el pasajero
        orden_destino: Int, orden de la parada donde baja el pasajero
    
    Returns:
        bool: True si el asiento está disponible en ese tramo
    """
    from .models import Pasaje
    
    pasajes_conflicto = Pasaje.objects.filter(
        viaje=viaje,
        asiento=asiento,
        estado__in=['reservado', 'vendido', 'abordado'],
        # Condición de solapamiento de segmentos:
        orden_origen__lt=orden_destino,   # El existente empieza antes de que termine el nuevo
        orden_destino__gt=orden_origen,   # El existente termina después de que empiece el nuevo
    )
    return not pasajes_conflicto.exists()


def obtener_asientos_disponibles(viaje, orden_origen, orden_destino):
    """
    Retorna los asientos disponibles para un tramo específico del viaje.
    
    Args:
        viaje: Instancia de Viaje
        orden_origen: Int, orden de la parada origen
        orden_destino: Int, orden de la parada destino
    
    Returns:
        QuerySet de Asiento disponibles para ese tramo
    """
    from .models import Pasaje
    
    todos_los_asientos = viaje.bus.asientos.all()
    
    # Obtener IDs de asientos ocupados en algún segmento del tramo solicitado
    asientos_ocupados_ids = Pasaje.objects.filter(
        viaje=viaje,
        estado__in=['reservado', 'vendido', 'abordado'],
        orden_origen__lt=orden_destino,
        orden_destino__gt=orden_origen,
    ).values_list('asiento_id', flat=True)
    
    return todos_los_asientos.exclude(id__in=asientos_ocupados_ids).order_by('numero_asiento')


def obtener_mapa_ocupacion(viaje):
    """
    Genera un mapa completo de ocupación de asientos por segmento.
    Útil para visualizar en el frontend qué asientos están libres u ocupados
    en cada tramo del itinerario.
    
    Args:
        viaje: Instancia de Viaje
    
    Returns:
        dict: {
            asiento_id: [
                {
                    'orden_origen': int,
                    'orden_destino': int,
                    'pasajero': str,
                    'codigo': str,
                    'estado': str,
                }
            ]
        }
    """
    from .models import Pasaje
    
    pasajes = Pasaje.objects.filter(
        viaje=viaje,
        estado__in=['reservado', 'vendido', 'abordado'],
    ).select_related('asiento', 'pasajero', 'parada_origen', 'parada_destino')
    
    mapa = {}
    for pasaje in pasajes:
        asiento_id = pasaje.asiento_id
        if asiento_id not in mapa:
            mapa[asiento_id] = []
        mapa[asiento_id].append({
            'orden_origen': pasaje.orden_origen,
            'orden_destino': pasaje.orden_destino,
            'parada_origen': str(pasaje.parada_origen),
            'parada_destino': str(pasaje.parada_destino),
            'pasajero': pasaje.pasajero.nombre_completo,
            'codigo': pasaje.codigo,
            'estado': pasaje.estado,
        })
    
    return mapa


def obtener_orden_parada(viaje, parada):
    """
    Obtiene el orden de una parada en el itinerario del viaje.
    
    Args:
        viaje: Instancia de Viaje
        parada: Instancia de Parada
    
    Returns:
        int: Orden de la parada, o None si no se encuentra
    """
    from itineraries.models import DetalleItinerario
    
    try:
        detalle = DetalleItinerario.objects.get(
            itinerario=viaje.itinerario,
            parada=parada,
        )
        return detalle.orden
    except DetalleItinerario.DoesNotExist:
        return None


def contar_asientos_disponibles_tramo(viaje, orden_origen, orden_destino):
    """
    Cuenta cuántos asientos están disponibles para un tramo específico.
    
    Args:
        viaje: Instancia de Viaje
        orden_origen: Int, orden de la parada origen
        orden_destino: Int, orden de la parada destino
    
    Returns:
        int: Número de asientos disponibles
    """
    return obtener_asientos_disponibles(viaje, orden_origen, orden_destino).count()
