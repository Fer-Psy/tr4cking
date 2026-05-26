"""
Utilidades para gestión de asientos por segmento.
Lógica core del sistema de ocupación de asientos.
"""
from django.db.models import Q
import unicodedata


def normalize_search(text):
    """
    Limpia texto para búsqueda: quita acentos, minúsculas y términos comunes.
    """
    if not text: return ""
    # Quitar acentos (NFD normalize)
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()
    # Quitar términos comunes de paradas
    return text.replace('terminal de ', '').replace('terminal ', '').replace('parada ', '').strip()


def get_similar_paradas_ids(parada_obj, base_id=None):
    """
    Retorna una lista de IDs de paradas que representan la misma ubicación física
    basándose en nombre y localidad, ignorando empresa y acentos.
    """
    if not parada_obj: 
        return [int(base_id)] if base_id else []
    
    from fleet.models import Parada
    
    norm = normalize_search(parada_obj.nombre)
    loc_norm = normalize_search(parada_obj.localidad.nombre if parada_obj.localidad else '')
    
    matched_ids = []
    if base_id:
        try:
            matched_ids.append(int(base_id))
        except (ValueError, TypeError):
            pass
    
    # Filtrar paradas en la misma localidad para reducir el set de búsqueda
    queryset = Parada.objects.all()
    if parada_obj.localidad:
        queryset = queryset.filter(localidad=parada_obj.localidad)
    
    for db_p in queryset.select_related('localidad'):
        if base_id and str(db_p.id) == str(base_id):
            continue
            
        db_norm = normalize_search(db_p.nombre)
        db_loc_norm = normalize_search(db_p.localidad.nombre if db_p.localidad else '')
        
        match = False
        if norm and norm == db_norm:
            match = True
        elif loc_norm and norm and (norm in db_loc_norm or db_loc_norm in norm):
            # Fallback por si el nombre de la parada es solo el nombre de la localidad
            match = True
            
        if match:
            matched_ids.append(db_p.id)
            
    return list(set(matched_ids))




def limpiar_reservas_expiradas():
    """
    Cancela automáticamente las reservas cuyo tiempo límite de pago ha expirado.
    """
    from .models import Pasaje
    from django.utils import timezone
    
    expiradas = Pasaje.objects.filter(
        estado='reservado',
        fecha_limite_pago__lt=timezone.now()
    )
    if expiradas.exists():
        expiradas.update(
            estado='cancelado',
            motivo_cancelacion='Reserva cancelada automáticamente (tiempo límite expirado)',
            fecha_cancelacion=timezone.now()
        )


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
    
    limpiar_reservas_expiradas()
    
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
    
    limpiar_reservas_expiradas()
    
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
    
    limpiar_reservas_expiradas()
    
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
            'vendedor_id': pasaje.vendedor_id,
        })
    
    return mapa


def obtener_orden_parada(viaje, parada):
    """
    Obtiene el orden de una parada en el itinerario del viaje.
    Si la parada exacta no está en el itinerario, busca paradas similares
    (mismo nombre/localidad) que sí estén en él.
    """
    from itineraries.models import DetalleItinerario
    
    # 1. Intento exacto
    detalle = DetalleItinerario.objects.filter(
        itinerario=viaje.itinerario,
        parada=parada,
    ).first()
    
    if detalle:
        return detalle.orden
        
    # 2. Intento por paradas similares (mismo nombre/localidad)
    similar_ids = get_similar_paradas_ids(parada, parada.id)
    detalle_similar = DetalleItinerario.objects.filter(
        itinerario=viaje.itinerario,
        parada_id__in=similar_ids
    ).first()
    
    if detalle_similar:
        return detalle_similar.orden
        
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
