/**
 * Función para confirmar acciones sensibles (Eliminar)
 */
function confirmarAccion(url, mensaje) {
    Swal.fire({
        title: '¿Estás seguro?',
        text: mensaje,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Sí, proceder',
        cancelButtonText: 'Cancelar'
    }).then((result) => {
        if (result.isConfirmed) {
            window.location.href = url;
        }
    });
}

/**
 * Captura y muestra los mensajes enviados desde Django
 */
document.addEventListener('DOMContentLoaded', function() {
    const mensajes = document.querySelectorAll('.django-message');
    
    mensajes.forEach(m => {
        const texto = m.dataset.texto;
        const tag = m.dataset.tag; 
        
        let icono = 'success';
        let titulo = '¡Éxito!';

        if (tag.includes('error') || tag.includes('danger')) {
            icono = 'error';
            titulo = 'Error';
        } else if (tag.includes('warning')) {
            icono = 'warning';
            titulo = 'Atención';
        } else if (tag.includes('info')) {
            icono = 'info';
            titulo = 'Información';
        }

        Swal.fire({
            title: titulo,
            text: texto,
            icon: icono,
            confirmButtonColor: '#39a900',
            timer: 3500,
            timerProgressBar: true
        });
    });
});