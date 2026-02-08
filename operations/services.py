"""
Servicios para facturación y timbrado.
Maneja la lógica de negocio de facturación, generación de PDF, QR, 
y reversión de movimientos de caja.
"""
import base64
import io
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.template.loader import render_to_string

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

from .models import (
    Factura, DetalleFactura, Timbrado, 
    SesionCaja, MovimientoCaja, Pasaje, Encomienda
)


class FacturacionService:
    """
    Servicio para manejar la lógica de facturación.
    """
    
    @staticmethod
    def obtener_timbrado_vigente(empresa=None):
        """
        Obtiene el timbrado vigente para la empresa.
        
        Args:
            empresa: Instancia de Empresa (opcional)
            
        Returns:
            Timbrado vigente o None
        """
        hoy = timezone.now().date()
        queryset = Timbrado.objects.filter(
            activo=True,
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy
        )
        
        if empresa:
            queryset = queryset.filter(empresa=empresa)
        
        return queryset.first()
    
    @staticmethod
    def validar_timbrado(timbrado):
        """
        Valida que un timbrado esté vigente y tenga números disponibles.
        
        Args:
            timbrado: Instancia de Timbrado
            
        Returns:
            tuple: (es_valido, mensaje_error)
        """
        if not timbrado:
            return False, "No se encontró un timbrado válido."
        
        if not timbrado.esta_vigente:
            return False, f"El timbrado {timbrado.numero} no está vigente."
        
        try:
            timbrado.get_siguiente_numero()
        except ValueError as e:
            return False, str(e)
        
        return True, None
    
    @staticmethod
    @transaction.atomic
    def crear_factura(timbrado, cliente, cajero, pasajes=None, encomiendas=None, 
                      condicion='contado', sesion_caja=None, tasa_iva=0):
        """
        Crea una factura completa con sus detalles.
        
        Args:
            timbrado: Instancia de Timbrado
            cliente: Instancia de Persona (cliente)
            cajero: Instancia de User (quien emite)
            pasajes: Lista de Pasajes a facturar (opcional)
            encomiendas: Lista de Encomiendas a facturar (opcional)
            condicion: 'contado' o 'credito'
            sesion_caja: Instancia de SesionCaja (opcional)
            tasa_iva: Tasa de IVA a aplicar (0, 5, 10)
            
        Returns:
            Factura creada
            
        Raises:
            ValueError: Si hay errores de validación
        """
        # Validar timbrado
        es_valido, error = FacturacionService.validar_timbrado(timbrado)
        if not es_valido:
            raise ValueError(error)
        
        # Validar que haya items
        if not pasajes and not encomiendas:
            raise ValueError("Debe incluir al menos un pasaje o encomienda.")
        
        # Crear la factura
        factura = Factura.objects.create(
            timbrado=timbrado,
            numero_factura=timbrado.get_siguiente_numero(),
            cliente=cliente,
            condicion=condicion,
            cajero=cajero,
            sesion_caja=sesion_caja
        )
        
        # Agregar detalles de pasajes
        if pasajes:
            for pasaje in pasajes:
                DetalleFactura.objects.create(
                    factura=factura,
                    cantidad=Decimal('1'),
                    descripcion=f"Pasaje {pasaje.parada_origen.nombre} - {pasaje.parada_destino.nombre}",
                    precio_unitario=pasaje.precio,
                    tasa_iva=tasa_iva,  # Transporte generalmente exento en Paraguay
                    subtotal=pasaje.precio,
                    pasaje=pasaje
                )
        
        # Agregar detalles de encomiendas
        if encomiendas:
            for encomienda in encomiendas:
                DetalleFactura.objects.create(
                    factura=factura,
                    cantidad=Decimal('1'),
                    descripcion=f"Encomienda {encomienda.tipo} - {encomienda.codigo}",
                    precio_unitario=encomienda.precio,
                    tasa_iva=10,  # Encomiendas generalmente gravadas 10%
                    subtotal=encomienda.precio,
                    encomienda=encomienda
                )
        
        # Calcular totales
        factura.calcular_totales()
        factura.save()
        
        # Registrar movimiento de caja si hay sesión abierta
        if sesion_caja and sesion_caja.estado == 'abierta':
            FacturacionService._registrar_movimiento_caja(
                sesion=sesion_caja,
                factura=factura,
                tipo='ingreso'
            )
        
        return factura
    
    @staticmethod
    @transaction.atomic
    def anular_factura(factura, motivo, usuario, revertir_caja=True):
        """
        Anula una factura y opcionalmente revierte el movimiento de caja.
        
        Args:
            factura: Instancia de Factura
            motivo: Motivo de anulación
            usuario: Usuario que anula
            revertir_caja: Si debe crear movimiento de egreso para revertir
            
        Returns:
            Factura anulada
        """
        if factura.estado == 'anulada':
            raise ValueError("La factura ya está anulada.")
        
        factura.estado = 'anulada'
        factura.fecha_anulacion = timezone.now()
        factura.motivo_anulacion = motivo
        factura.save()
        
        # Revertir movimiento de caja
        if revertir_caja:
            # Buscar sesión de caja activa del usuario
            try:
                sesion = SesionCaja.objects.get(
                    cajero=usuario,
                    estado='abierta'
                )
                
                # Crear movimiento de egreso para revertir
                MovimientoCaja.objects.create(
                    sesion=sesion,
                    tipo='egreso',
                    concepto='anulacion',
                    monto=factura.total,
                    descripcion=f"Anulación factura {factura.numero_completo}",
                    factura=factura
                )
            except SesionCaja.DoesNotExist:
                pass  # No hay caja abierta, no se puede revertir
        
        # Actualizar estado de pasajes relacionados si corresponde
        for detalle in factura.detalles.filter(pasaje__isnull=False):
            if detalle.pasaje:
                detalle.pasaje.estado = 'cancelado'
                detalle.pasaje.fecha_cancelacion = timezone.now()
                detalle.pasaje.motivo_cancelacion = f"Factura anulada: {motivo}"
                detalle.pasaje.save()
        
        return factura
    
    @staticmethod
    def _registrar_movimiento_caja(sesion, factura, tipo='ingreso'):
        """
        Registra un movimiento de caja asociado a una factura.
        """
        # Determinar concepto según tipo de items
        tiene_pasajes = factura.detalles.filter(pasaje__isnull=False).exists()
        tiene_encomiendas = factura.detalles.filter(encomienda__isnull=False).exists()
        
        if tiene_pasajes and tiene_encomiendas:
            concepto = 'otro'
            descripcion = f"Venta {factura.numero_completo}"
        elif tiene_pasajes:
            concepto = 'venta_pasaje'
            descripcion = f"Pasaje {factura.numero_completo}"
        else:
            concepto = 'venta_encomienda'
            descripcion = f"Encomienda {factura.numero_completo}"
        
        MovimientoCaja.objects.create(
            sesion=sesion,
            tipo=tipo,
            concepto=concepto,
            monto=factura.total,
            descripcion=descripcion,
            factura=factura
        )
    
    @staticmethod
    def generar_qr_factura(factura):
        """
        Genera el código QR para la factura con los datos fiscales.
        
        Args:
            factura: Instancia de Factura
            
        Returns:
            String base64 de la imagen QR o None si no está disponible
        """
        if not HAS_QRCODE:
            return None
        
        # Datos para el QR (formato simplificado)
        # En producción, usar el formato requerido por la SET
        qr_data = (
            f"RUC:{factura.timbrado.empresa.ruc}|"
            f"TIMBRADO:{factura.timbrado.numero}|"
            f"FACTURA:{factura.numero_completo}|"
            f"FECHA:{factura.fecha_emision.strftime('%Y%m%d')}|"
            f"TOTAL:{factura.total}|"
            f"IVA:{factura.total_iva}"
        )
        
        # Generar QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    @staticmethod
    def numero_a_letras(numero):
        """
        Convierte un número a texto en español.
        
        Args:
            numero: Número entero a convertir
            
        Returns:
            String con el número en letras
        """
        if numero == 0:
            return "CERO GUARANÍES"
        
        unidades = ['', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE']
        decenas = ['', 'DIEZ', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA', 
                   'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
        especiales = {
            11: 'ONCE', 12: 'DOCE', 13: 'TRECE', 14: 'CATORCE', 15: 'QUINCE',
            16: 'DIECISÉIS', 17: 'DIECISIETE', 18: 'DIECIOCHO', 19: 'DIECINUEVE'
        }
        centenas = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS',
                    'QUINIENTOS', 'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']
        
        def convertir_grupo(n):
            """Convierte un número de 3 dígitos."""
            if n == 0:
                return ''
            if n == 100:
                return 'CIEN'
            
            resultado = ''
            
            # Centenas
            if n >= 100:
                resultado = centenas[n // 100]
                n = n % 100
                if n > 0:
                    resultado += ' '
            
            # Especiales (11-19)
            if n in especiales:
                return resultado + especiales[n]
            
            # Decenas
            if n >= 10:
                if n == 20:
                    resultado += 'VEINTE'
                elif 21 <= n <= 29:
                    resultado += 'VEINTI' + unidades[n - 20]
                else:
                    resultado += decenas[n // 10]
                    if n % 10 > 0:
                        resultado += ' Y ' + unidades[n % 10]
                return resultado
            
            # Unidades
            if n > 0:
                resultado += unidades[n]
            
            return resultado
        
        # Convertir el número completo
        numero = int(numero)
        
        if numero < 1000:
            texto = convertir_grupo(numero)
        elif numero < 1000000:
            miles = numero // 1000
            resto = numero % 1000
            if miles == 1:
                texto = 'MIL'
            else:
                texto = convertir_grupo(miles) + ' MIL'
            if resto > 0:
                texto += ' ' + convertir_grupo(resto)
        else:
            millones = numero // 1000000
            resto = numero % 1000000
            if millones == 1:
                texto = 'UN MILLÓN'
            else:
                texto = convertir_grupo(millones) + ' MILLONES'
            if resto > 0:
                texto += ' ' + FacturacionService.numero_a_letras(resto).replace(' GUARANÍES', '')
        
        return texto + ' GUARANÍES'
    
    @staticmethod
    def generar_pdf_factura(factura):
        """
        Genera un PDF de la factura para descarga.
        Requiere weasyprint o reportlab.
        
        Args:
            factura: Instancia de Factura
            
        Returns:
            bytes del PDF generado
        """
        try:
            from weasyprint import HTML
            
            # Preparar contexto
            detalles = factura.detalles.all()
            primer_pasaje = None
            for d in detalles:
                if d.pasaje:
                    primer_pasaje = d.pasaje
                    break
            
            context = {
                'factura': factura,
                'detalles': detalles,
                'empresa': factura.timbrado.empresa,
                'primer_detalle_pasaje': primer_pasaje,
                'total_letras': FacturacionService.numero_a_letras(int(factura.total)),
                'qr_image': FacturacionService.generar_qr_factura(factura),
            }
            
            # Renderizar HTML
            html_string = render_to_string('operations/factura_ticket.html', context)
            
            # Generar PDF
            html = HTML(string=html_string)
            pdf = html.write_pdf()
            
            return pdf
            
        except ImportError:
            # Si no está weasyprint, intentar con reportlab
            return FacturacionService._generar_pdf_reportlab(factura)
    
    @staticmethod
    def _generar_pdf_reportlab(factura):
        """
        Genera PDF usando reportlab como fallback.
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.pdfgen import canvas
            
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=(80*mm, 297*mm))  # Ancho 80mm para ticket
            
            y = 290*mm  # Empezar desde arriba
            
            # Encabezado
            p.setFont("Courier-Bold", 12)
            p.drawCentredString(40*mm, y, factura.timbrado.empresa.nombre)
            y -= 5*mm
            
            p.setFont("Courier", 8)
            p.drawCentredString(40*mm, y, f"RUC: {factura.timbrado.empresa.ruc}")
            y -= 7*mm
            
            # Factura
            p.setFont("Courier-Bold", 10)
            p.drawCentredString(40*mm, y, "FACTURA ELECTRÓNICA")
            y -= 5*mm
            p.drawCentredString(40*mm, y, factura.numero_completo)
            y -= 5*mm
            
            p.setFont("Courier", 8)
            p.drawString(3*mm, y, f"Timbrado: {factura.timbrado.numero}")
            y -= 4*mm
            p.drawString(3*mm, y, f"Cliente: {factura.cliente.cedula}")
            y -= 4*mm
            p.drawString(3*mm, y, factura.cliente.nombre_completo[:30])
            y -= 6*mm
            
            # Detalles
            p.drawString(3*mm, y, "-" * 42)
            y -= 4*mm
            
            for detalle in factura.detalles.all():
                p.drawString(3*mm, y, f"1 x {detalle.descripcion[:25]}")
                y -= 4*mm
                p.drawRightString(77*mm, y, f"Gs. {int(detalle.subtotal):,}")
                y -= 5*mm
            
            # Total
            p.drawString(3*mm, y, "-" * 42)
            y -= 5*mm
            p.setFont("Courier-Bold", 11)
            p.drawRightString(77*mm, y, f"TOTAL: Gs. {int(factura.total):,}")
            
            p.showPage()
            p.save()
            
            buffer.seek(0)
            return buffer.getvalue()
            
        except ImportError:
            raise ImportError("Se requiere weasyprint o reportlab para generar PDFs")


class TicketService:
    """
    Servicio para impresión de tickets.
    """
    
    @staticmethod
    def preparar_contexto_ticket(factura):
        """
        Prepara el contexto para renderizar el ticket.
        
        Args:
            factura: Instancia de Factura
            
        Returns:
            dict con el contexto para el template
        """
        detalles = factura.detalles.select_related(
            'pasaje__viaje__itinerario',
            'pasaje__viaje__bus',
            'pasaje__pasajero',
            'pasaje__asiento',
            'pasaje__parada_origen',
            'pasaje__parada_destino',
            'encomienda'
        ).all()
        
        primer_pasaje = None
        for d in detalles:
            if d.pasaje:
                primer_pasaje = d.pasaje
                break
        
        return {
            'factura': factura,
            'detalles': detalles,
            'empresa': factura.timbrado.empresa,
            'primer_detalle_pasaje': primer_pasaje,
            'total_letras': FacturacionService.numero_a_letras(int(factura.total)),
            'qr_image': FacturacionService.generar_qr_factura(factura),
        }
    
    @staticmethod
    def generar_comandos_impresora(factura):
        """
        Genera comandos ESC/POS para impresión directa.
        Útil para integración con impresoras térmicas vía JavaScript.
        
        Args:
            factura: Instancia de Factura
            
        Returns:
            bytes con comandos ESC/POS
        """
        # Comandos ESC/POS básicos
        ESC = b'\x1b'
        GS = b'\x1d'
        
        INIT = ESC + b'@'  # Inicializar impresora
        CENTER = ESC + b'a' + b'\x01'  # Centrar
        LEFT = ESC + b'a' + b'\x00'  # Alinear izquierda
        RIGHT = ESC + b'a' + b'\x02'  # Alinear derecha
        BOLD_ON = ESC + b'E' + b'\x01'
        BOLD_OFF = ESC + b'E' + b'\x00'
        DOUBLE_HEIGHT = GS + b'!' + b'\x10'
        NORMAL = GS + b'!' + b'\x00'
        CUT = GS + b'V' + b'\x00'  # Corte total
        
        def line(text):
            return text.encode('cp850', errors='replace') + b'\n'
        
        commands = INIT
        
        # Encabezado
        commands += CENTER + BOLD_ON + DOUBLE_HEIGHT
        commands += line(factura.timbrado.empresa.nombre)
        commands += NORMAL + BOLD_OFF
        commands += line(f"RUC: {factura.timbrado.empresa.ruc}")
        commands += line("-" * 42)
        
        # Número de factura
        commands += BOLD_ON
        commands += line("FACTURA ELECTRONICA")
        commands += line(factura.numero_completo)
        commands += BOLD_OFF
        commands += line(f"Timbrado: {factura.timbrado.numero}")
        commands += LEFT
        
        # Cliente
        commands += line("-" * 42)
        commands += line(f"Cliente: {factura.cliente.cedula}")
        commands += line(factura.cliente.nombre_completo[:42])
        commands += line("-" * 42)
        
        # Detalles
        for detalle in factura.detalles.all():
            desc = detalle.descripcion[:30]
            precio = f"Gs. {int(detalle.subtotal):,}"
            commands += line(f"1 {desc}")
            commands += RIGHT + line(precio) + LEFT
        
        # Total
        commands += line("-" * 42)
        commands += CENTER + BOLD_ON + DOUBLE_HEIGHT
        commands += line(f"TOTAL: Gs. {int(factura.total):,}")
        commands += NORMAL + BOLD_OFF
        
        # Fecha
        commands += line("")
        commands += line(factura.fecha_emision.strftime("%d/%m/%Y %H:%M"))
        commands += line("GRACIAS POR SU PREFERENCIA")
        
        # Corte
        commands += line("") * 3
        commands += CUT
        
        return commands
