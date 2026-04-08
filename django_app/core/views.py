from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Cliente, Producto, Pedido, DetallePedido
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings 
from django.db.models import ProtectedError, Sum, Count, Q, Value
from django.db.models.functions import Coalesce, TruncMonth
import json 
from xhtml2pdf import pisa
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

# --- DASHBOARD ---

def dashboard(request):
    # 1. Total de pedidos entregados
    pedidos_entregados = Pedido.objects.filter(estado='Entregado').count()
    
    # 2. Total unidades vendidas (Solo de pedidos entregados)
    total_unidades = DetallePedido.objects.filter(pedido__estado='Entregado').aggregate(Sum('cantidad'))['cantidad__sum'] or 0

    # 3. TOP 3 MÁS VENDIDOS
    mas_vendidos = Producto.objects.annotate(
        total_real=Coalesce(Sum('detallepedido__cantidad', filter=Q(detallepedido__pedido__estado='Entregado')), Value(0))
    ).filter(total_real__gt=0).order_by('-total_real')[:3]

    # 4. TOP 3 MENOS VENDIDOS
    menos_vendidos = Producto.objects.annotate(
        total_real=Coalesce(Sum('detallepedido__cantidad', filter=Q(detallepedido__pedido__estado='Entregado')), Value(0))
    ).order_by('total_real')[:3]

    # 5. Gráfico de ventas por MES
    # Forzamos el truncado a mes
    ventas_query = Pedido.objects.annotate(mes_trunc=TruncMonth('fecha')) \
        .values('mes_trunc') \
        .annotate(total=Count('id')) \
        .order_by('mes_trunc')

    meses_nombres = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
    }

    fechas_lista = []
    cantidades_lista = []

    for v in ventas_query:
        # v['mes_trunc'] es un objeto datetime o date al inicio del mes
        if v['mes_trunc']:
            etiqueta = f"{meses_nombres[v['mes_trunc'].month]} {v['mes_trunc'].year}"
            fechas_lista.append(etiqueta)
            cantidades_lista.append(v['total'])

    context = {
        'pedidos_entregados': pedidos_entregados,
        'total_unidades': total_unidades,
        'mas_vendidos': mas_vendidos,
        'menos_vendidos': menos_vendidos,
        'fechas_json': json.dumps(fechas_lista),
        'cantidades_json': json.dumps(cantidades_lista),
    }
    return render(request, 'core/dashboard.html', context)

# --- GESTIÓN DE CLIENTES ---

def listar_clientes(request):
    clientes_qs = Cliente.objects.all().order_by('-id')
    paginator = Paginator(clientes_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/clientes_list.html', {'page_obj': page_obj})

def crear_cliente(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        correo = request.POST.get('correo', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        telefono = request.POST.get('telefono', '').strip()

        # Validar campos vacíos
        if not nombre or not correo:
            messages.error(request, "El nombre y el correo son obligatorios.")
            return render(request, 'core/cliente_form.html')

        # Validar duplicados (correo único)
        if Cliente.objects.filter(correo=correo).exists():
            messages.error(request, f"Ya existe un cliente con el correo {correo}.")
            return render(request, 'core/cliente_form.html')

        Cliente.objects.create(
            nombre=nombre, correo=correo, direccion=direccion, telefono=telefono
        )
        messages.success(request, 'Se ha Creado el Cliente Satisfactoriamente')
        return redirect('listar_clientes')
    return render(request, 'core/cliente_form.html')

def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        correo = request.POST.get('correo', '').strip()

        if not nombre or not correo:
            messages.error(request, "Campos obligatorios vacíos.")
            return render(request, 'core/cliente_form.html', {'cliente': cliente})

        # Validar duplicados excluyendo al cliente actual
        if Cliente.objects.filter(correo=correo).exclude(id=id).exists():
            messages.error(request, "Este correo ya pertenece a otro cliente.")
            return render(request, 'core/cliente_form.html', {'cliente': cliente})

        cliente.nombre = nombre
        cliente.correo = correo
        cliente.direccion = request.POST.get('direccion')
        cliente.telefono = request.POST.get('telefono')
        cliente.save()
        messages.success(request, 'Se ha Actualizado el Cliente Satisfactoriamente')
        return redirect('listar_clientes')
    return render(request, 'core/cliente_form.html', {'cliente': cliente})

def eliminar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    try:
        # Verificamos manualmente antes de intentar borrar
        if cliente.pedido_set.exists():
            messages.error(request, f'No es posible eliminar a "{cliente.nombre}" porque tiene pedidos registrados en el historial.')
            return redirect('listar_clientes')
        
        cliente.delete()
        messages.success(request, 'Cliente eliminado satisfactoriamente.')
    except ProtectedError:
        messages.error(request, 'Error de integridad: El cliente tiene registros protegidos vinculados.')
    
    return redirect('listar_clientes')

# --- GESTIÓN DE PRODUCTOS ---

def listar_productos(request):
    productos_qs = Producto.objects.all().order_by('-id')
    paginator = Paginator(productos_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/productos_list.html', {'page_obj': page_obj})

def crear_producto(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        precio_raw = request.POST.get('precio')
        stock_raw = request.POST.get('stock')

        # Validar vacíos
        if not nombre or not precio_raw or not stock_raw:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, 'core/producto_form.html')

        # Validar duplicados por nombre (insensible a mayúsculas con __iexact)
        if Producto.objects.filter(nombre__iexact=nombre).exists():
            messages.error(request, f"El producto '{nombre}' ya existe.")
            return render(request, 'core/producto_form.html')

        try:
            precio = float(precio_raw)
            stock = int(stock_raw)
            if stock < 0 or precio <= 0:
                messages.error(request, "Precio debe ser positivo y stock no puede ser negativo.")
                return render(request, 'core/producto_form.html')
            
            Producto.objects.create(nombre=nombre, precio=precio, stock=stock)
            messages.success(request, 'Se ha Creado el Producto Satisfactoriamente')
            return redirect('listar_productos')
        except ValueError:
            messages.error(request, "Datos numéricos inválidos.")
    return render(request, 'core/producto_form.html')

def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        
        if not nombre:
            messages.error(request, "El nombre no puede estar vacío.")
            return render(request, 'core/producto_form.html', {'producto': producto})

        # Validar duplicados excluyendo el producto actual
        if Producto.objects.filter(nombre__iexact=nombre).exclude(id=id).exists():
            messages.error(request, f"Ya existe otro producto llamado '{nombre}'.")
            return render(request, 'core/producto_form.html', {'producto': producto})

        try:
            producto.nombre = nombre
            producto.precio = request.POST.get('precio')
            producto.stock = int(request.POST.get('stock'))
            if producto.stock < 0:
                messages.error(request, "El stock no puede ser negativo.")
                return render(request, 'core/producto_form.html', {'producto': producto})
            
            producto.save()
            messages.success(request, 'Se ha Actualizado el Producto Satisfactoriamente')
            return redirect('listar_productos')
        except ValueError:
            messages.error(request, "Error en los datos numéricos.")
            
    return render(request, 'core/producto_form.html', {'producto': producto})

def eliminar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    try:
        # Verificamos si el producto aparece en algún detalle de pedido
        if producto.detallepedido_set.exists():
            messages.error(request, f'No se puede eliminar "{producto.nombre}" porque ya forma parte de pedidos existentes.')
            return redirect('listar_productos')
        
        producto.delete()
        messages.success(request, 'Producto eliminado satisfactoriamente.')
    except ProtectedError:
        messages.error(request, 'Error de integridad: El producto está referenciado en pedidos que no se pueden borrar.')
        
    return redirect('listar_productos')

# --- GESTIÓN DE PEDIDOS ---

def listar_pedidos(request):
    # Usamos annotate para sumar todos los subtotales de los detalles de cada pedido
    pedidos_qs = Pedido.objects.annotate(
        total_general=Sum('detalles__subtotal')
    ).all().order_by('-id')
    
    paginator = Paginator(pedidos_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'core/pedidos_list.html', {'page_obj': page_obj})

def ver_pedido(request, id):
    pedido = get_object_or_404(Pedido, id=id)
    return render(request, 'core/pedido_detalle.html', {'pedido': pedido})

def crear_pedido(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        estado = request.POST.get('estado')
        productos_ids = request.POST.getlist('producto[]') # Captura la lista del HTML
        cantidades = request.POST.getlist('cantidad[]')   # Captura la lista del HTML

        if not cliente_id or not productos_ids:
            messages.error(request, "Debe seleccionar un cliente y al menos un producto.")
            return redirect('crear_pedido')

        try:
            cliente = get_object_or_404(Cliente, id=cliente_id)
            pedido = Pedido.objects.create(cliente=cliente, estado=estado)
            
            # Recorremos cada producto enviado
            for p_id, cant in zip(productos_ids, cantidades):
                if not p_id or not cant: continue # Ignorar filas vacías
                
                prod = get_object_or_404(Producto, id=p_id)
                c_int = int(cant)

                if c_int <= prod.stock:
                    DetallePedido.objects.create(pedido=pedido, producto=prod, cantidad=c_int)
                    prod.stock -= c_int
                    prod.save()
                else:
                    messages.warning(request, f"Stock insuficiente para {prod.nombre}. Se omitió.")

            messages.success(request, 'Pedido creado satisfactoriamente.')
            return redirect('listar_pedidos')
        except ValueError:
            messages.error(request, "Datos de cantidades inválidos.")

    return render(request, 'core/pedido_form.html', {
        'clientes': Cliente.objects.all(),
        'productos': Producto.objects.all()
    })

def editar_pedido(request, id):
    pedido = get_object_or_404(Pedido, id=id)
    estado_anterior = pedido.estado

    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        nuevo_estado = request.POST.get('estado')
        productos_ids = request.POST.getlist('producto[]')
        cantidades = request.POST.getlist('cantidad[]')

        if not cliente_id or not productos_ids:
            messages.error(request, "El pedido no puede estar vacío.")
            return redirect('editar_pedido', id=id)

        # 1. Devolvemos stock de los productos que ya estaban cargados
        for det in pedido.detalles.all():
            p = det.producto
            p.stock += det.cantidad
            p.save()

        # 2. Si el pedido se marca como Cancelado
        if nuevo_estado == 'Cancelado' and estado_anterior != 'Cancelado':
            pedido.estado = nuevo_estado
            pedido.save()
            # Ya devolvimos el stock en el paso 1, así que solo borramos detalles
            pedido.detalles.all().delete()
            messages.success(request, 'Pedido cancelado y stock devuelto.')
            return redirect('listar_pedidos')

        # 3. Borramos los detalles viejos para crear los nuevos
        pedido.detalles.all().delete()
        
        # 4. Actualizamos datos básicos
        pedido.cliente_id = cliente_id
        pedido.estado = nuevo_estado
        pedido.save()

        # 5. Creamos los nuevos detalles (y restamos stock de nuevo)
        for p_id, cant in zip(productos_ids, cantidades):
            if not p_id or not cant: continue
            
            prod = get_object_or_404(Producto, id=p_id)
            c_int = int(cant)

            if c_int <= prod.stock:
                DetallePedido.objects.create(pedido=pedido, producto=prod, cantidad=c_int)
                prod.stock -= c_int
                prod.save()
            else:
                messages.error(request, f"No hay stock para {prod.nombre}. Disponible: {prod.stock}")

        messages.success(request, 'Pedido actualizado satisfactoriamente.')
        return redirect('listar_pedidos')

    return render(request, 'core/pedido_form.html', {
        'pedido': pedido,
        'clientes': Cliente.objects.all(),
        'productos': Producto.objects.all()
    })

# -- REPORTES Y AUTH --

def exportar_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte de Pedidos"
    
    # Encabezados actualizados
    ws.append(['Fecha', 'Cliente', 'Productos (Cant)', 'Estado', 'Total Pedido'])
    
    # Consulta optimizada con la suma total
    pedidos = Pedido.objects.annotate(
        total_pedido=Sum('detalles__subtotal')
    ).prefetch_related('detalles__producto', 'cliente').order_by('-id')

    for p in pedidos:
        # Creamos una lista de productos en formato texto: "Manzana (x2), Pera (x5)"
        detalles_texto = ", ".join([
            f"{d.producto.nombre} (x{d.cantidad})" for d in p.detalles.all()
        ])
        
        ws.append([
            p.fecha.strftime("%d/%m/%Y %H:%M"),
            p.cliente.nombre,
            detalles_texto,
            p.estado,
            p.total_pedido or 0
        ])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Reporte_Pedidos.xlsx"'
    wb.save(response)
    return response

def exportar_pdf(request):
    # Anotamos el total para que esté disponible en el template como p.total_pedido
    pedidos = Pedido.objects.annotate(
        total_pedido=Sum('detalles__subtotal')
    ).prefetch_related('detalles__producto', 'cliente').order_by('-id')
    
    template = get_template('core/reporte_pdf.html')
    html = template.render({'pedidos': pedidos})
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Reporte_Pedidos.pdf"'
    
    # pisa es el alias común para xhtml2pdf
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    return response

def logout_view(request):
    if 'auth_token' in request.session:
        del request.session['auth_token']
    return redirect(settings.LOGIN_URL_EXTERNAL)