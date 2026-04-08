from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Cliente, Producto, Pedido, DetallePedido
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings  # <--- IMPORTANTE: Necesario para el logout
from xhtml2pdf import pisa
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

# GESTIÓN DE CLIENTES

def listar_clientes(request):
    clientes_qs = Cliente.objects.all().order_by('-id')
    paginator = Paginator(clientes_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'core/clientes_list.html', {'page_obj': page_obj})

def crear_cliente(request):
    if request.method == 'POST':
        Cliente.objects.create(
            nombre=request.POST.get('nombre'),
            correo=request.POST.get('correo'),
            direccion=request.POST.get('direccion'),
            telefono=request.POST.get('telefono')
        )
        messages.success(request, 'Se ha Creado el Cliente Satisfactoriamente')
        return redirect('listar_clientes')
    return render(request, 'core/cliente_form.html')

def editar_cliente(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    if request.method == 'POST':
        cliente.nombre = request.POST.get('nombre')
        cliente.correo = request.POST.get('correo')
        cliente.direccion = request.POST.get('direccion')
        cliente.telefono = request.POST.get('telefono')
        cliente.save()
        messages.success(request, 'Se ha Actualizado el Cliente Satisfactoriamente')
        return redirect('listar_clientes')
    return render(request, 'core/cliente_form.html', {'cliente': cliente})

def eliminar_cliente(request, id):
    get_object_or_404(Cliente, id=id).delete()
    messages.success(request, 'Se ha Eliminado el Cliente Satisfactoriamente')
    return redirect('listar_clientes')

# GESTIÓN DE PRODUCTOS

def listar_productos(request):
    productos_qs = Producto.objects.all().order_by('-id')
    paginator = Paginator(productos_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'core/productos_list.html', {'page_obj': page_obj})

def crear_producto(request):
    if request.method == 'POST':
        try:
            stock = int(request.POST.get('stock'))
            if stock < 0:
                messages.error(request, "El stock no puede ser negativo")
                return redirect('crear_producto')
            
            Producto.objects.create(
                nombre=request.POST.get('nombre'),
                precio=request.POST.get('precio'),
                stock=stock
            )
            messages.success(request, 'Se ha Creado el Producto Satisfactoriamente')
            return redirect('listar_productos')
        except ValueError:
            messages.error(request, "Datos de precio o stock inválidos")
            
    return render(request, 'core/producto_form.html')

def editar_producto(request, id):
    producto = get_object_or_404(Producto, id=id)
    if request.method == 'POST':
        producto.nombre = request.POST.get('nombre')
        producto.precio = request.POST.get('precio')
        producto.stock = request.POST.get('stock')
        producto.save()
        messages.success(request, 'Se ha Actualizado el Producto Satisfactoriamente')
        return redirect('listar_productos')
    return render(request, 'core/producto_form.html', {'producto': producto})

def eliminar_producto(request, id):
    get_object_or_404(Producto, id=id).delete()
    messages.success(request, 'Se ha Eliminado el Producto Satisfactoriamente')
    return redirect('listar_productos')

# GESTIÓN DE PEDIDOS CON CONTROL DE STOCK

def listar_pedidos(request):
    pedidos_qs = Pedido.objects.all().order_by('-id')
    paginator = Paginator(pedidos_qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'core/pedidos_list.html', {'page_obj': page_obj})

def crear_pedido(request):
    if request.method == 'POST':
        producto = get_object_or_404(Producto, id=request.POST.get('producto'))
        cantidad = int(request.POST.get('cantidad'))

        if cantidad > producto.stock:
            messages.error(request, f"Stock insuficiente. Solo quedan {producto.stock} unidades de {producto.nombre}.")
            return redirect('crear_pedido')

        cliente = get_object_or_404(Cliente, id=request.POST.get('cliente'))
        pedido = Pedido.objects.create(cliente=cliente, estado=request.POST.get('estado'))
        DetallePedido.objects.create(pedido=pedido, producto=producto, cantidad=cantidad)

        # Descontar stock
        producto.stock -= cantidad
        producto.save()

        messages.success(request, 'Se ha Creado el Pedido Satisfactoriamente')
        return redirect('listar_pedidos')
    
    return render(request, 'core/pedido_form.html', {
        'clientes': Cliente.objects.all(),
        'productos': Producto.objects.all()
    })

def editar_pedido(request, id):
    pedido = get_object_or_404(Pedido, id=id)
    detalle = pedido.detalles.first()
    
    producto_anterior = detalle.producto
    cantidad_anterior = detalle.cantidad

    if request.method == 'POST':
        nuevo_prod_id = request.POST.get('producto')
        nueva_cantidad = int(request.POST.get('cantidad'))
        nuevo_producto = get_object_or_404(Producto, id=nuevo_prod_id)

        # Mismo producto, cambió cantidad
        if nuevo_producto == producto_anterior:
            diferencia = nueva_cantidad - cantidad_anterior
            if diferencia > producto_anterior.stock:
                messages.error(request, f"No hay stock suficiente. Disponible: {producto_anterior.stock}")
                return redirect('editar_pedido', id=id)
            producto_anterior.stock -= diferencia
            producto_anterior.save()

        # Cambio producto
        else:
            if nueva_cantidad > nuevo_producto.stock:
                messages.error(request, f"Stock insuficiente en {nuevo_producto.nombre}")
                return redirect('editar_pedido', id=id)
            producto_anterior.stock += cantidad_anterior
            producto_anterior.save()
            nuevo_producto.stock -= nueva_cantidad
            nuevo_producto.save()

        pedido.cliente_id = request.POST.get('cliente')
        pedido.estado = request.POST.get('estado')
        pedido.save()

        detalle.producto = nuevo_producto
        detalle.cantidad = nueva_cantidad
        detalle.save()

        messages.success(request, 'Se ha Actualizado el Pedido Satisfactoriamente')
        return redirect('listar_pedidos')
    
    return render(request, 'core/pedido_form.html', {
        'pedido': pedido,
        'detalle': detalle,
        'clientes': Cliente.objects.all(),
        'productos': Producto.objects.all()
    })

def eliminar_pedido(request, id):
    pedido = get_object_or_404(Pedido, id=id)
    for det in pedido.detalles.all():
        prod = det.producto
        prod.stock += det.cantidad
        prod.save()
    
    pedido.delete()
    messages.success(request, 'Se ha Eliminado el Pedido Satisfactoriamente')
    return redirect('listar_pedidos')

# -- REPORTES --

def exportar_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte Detallado de Pedidos"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="39a900", end_color="39a900", fill_type="solid")
    center_alignment = Alignment(horizontal="center")
    money_format = '"$"#,##0'

    columns = ['Fecha', 'Cliente', 'Producto', 'Cant.', 'Precio Unit.', 'Subtotal']
    ws.append(columns)

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment

    pedidos = Pedido.objects.all().prefetch_related('detalles__producto', 'cliente')

    for p in pedidos:
        for d in p.detalles.all():
            row = [
                p.fecha.strftime("%d/%m/%Y"),
                p.cliente.nombre,
                d.producto.nombre,
                d.cantidad,
                d.producto.precio,
                d.subtotal
            ]
            ws.append(row)
            
            last_row = ws.max_row
            ws.cell(row=last_row, column=5).number_format = money_format
            ws.cell(row=last_row, column=6).number_format = money_format

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        ws.column_dimensions[column].width = max_length + 2

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Reporte_Pedidos.xlsx"'
    wb.save(response)
    return response

def exportar_pdf(request):
    pedidos = Pedido.objects.all()
    template = get_template('core/reporte_pdf.html')
    html = template.render({'pedidos': pedidos})
    response = HttpResponse(content_type='application/pdf')
    pisa_status = pisa.CreatePDF(html, dest=response)
    return response

# -- AUTENTICACIÓN / CIERRE DE SESIÓN --

def logout_view(request):
    """
    Cierra la sesión de Django eliminando el token JWT de la sesión
    y redirige al usuario a la API externa de FastAPI (Login).
    """
    if 'auth_token' in request.session:
        del request.session['auth_token']
    
    # Redirige a la URL de login definida en settings (http://127.0.0.1:8001/)
    return redirect(settings.LOGIN_URL_EXTERNAL)