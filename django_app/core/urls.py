from django.urls import path
from . import views

urlpatterns = [
    # Pedidos
    path('pedidos/', views.listar_pedidos, name='listar_pedidos'),
    path('pedidos/ver/<int:id>/', views.ver_pedido, name='ver_pedido'),
    path('pedidos/nuevo/', views.crear_pedido, name='crear_pedido'),
    path('pedidos/editar/<int:id>/', views.editar_pedido, name='editar_pedido'),
    path('pedidos/excel/', views.exportar_excel, name='exportar_excel'),
    path('pedidos/pdf/', views.exportar_pdf, name='exportar_pdf'),

    # Clientes
    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('clientes/nuevo/', views.crear_cliente, name='crear_cliente'),
    path('clientes/editar/<int:id>/', views.editar_cliente, name='editar_cliente'),
    path('clientes/eliminar/<int:id>/', views.eliminar_cliente, name='eliminar_cliente'),

    # Productos
    path('productos/', views.listar_productos, name='listar_productos'),
    path('productos/nuevo/', views.crear_producto, name='crear_producto'),
    path('productos/editar/<int:id>/', views.editar_producto, name='editar_producto'),
    path('productos/eliminar/<int:id>/', views.eliminar_producto, name='eliminar_producto'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # API
    path('logout/', views.logout_view, name='logout'),
]