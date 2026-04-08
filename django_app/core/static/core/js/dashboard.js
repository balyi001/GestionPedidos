document.addEventListener('DOMContentLoaded', function () {
    const chartElement = document.getElementById('salesChart');
    
    if (chartElement) {
        // Obtenemos los datos de los atributos 'data-' del canvas
        const fechas = JSON.parse(chartElement.getAttribute('data-fechas'));
        const cantidades = JSON.parse(chartElement.getAttribute('data-cantidades'));

        const ctx = chartElement.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: fechas,
                datasets: [{
                    label: 'Cantidad de Pedidos',
                    data: cantidades,
                    borderColor: '#39a900',
                    backgroundColor: 'rgba(57, 169, 0, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, ticks: { stepSize: 1 } }
                }
            }
        });
    }
});