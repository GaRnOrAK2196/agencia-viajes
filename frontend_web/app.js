document.addEventListener('DOMContentLoaded', () => {

  const formBusqueda = document.getElementById('form-busqueda');
  const resultadosContainer = document.getElementById('resultados-busqueda');

  // El 'escuchador' principal sigue siendo 'async'
  formBusqueda.addEventListener('submit', async (event) => {
    event.preventDefault();

    const origen = document.getElementById('origen').value.trim();
    const destino = document.getElementById('destino').value.trim();
    const fechaInput = document.getElementById('fecha').value;

    // Validación: Origen diferente a destino
    if (origen.toLowerCase() === destino.toLowerCase()) {
      alert("El origen y el destino no pueden ser iguales.");
      return; // Detenemos la función
    }

    // Validación: Fecha mayor o igual a hoy
    const fechaSeleccionada = new Date(fechaInput);
    // Creamos una fecha de "hoy" y le quitamos la hora para comparar solo días
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    // Ajustamos la fecha seleccionada para compensar la zona horaria (truco KIS)
    const fechaSeleccionadaAjustada = new Date(fechaSeleccionada.getTime() + fechaSeleccionada.getTimezoneOffset() * 60000);

    if (fechaSeleccionadaAjustada < hoy) {
      alert("La fecha del viaje debe de ser mayor a la actual.");
      return;
    }

    console.log("Búsqueda iniciada...");

    resultadosContainer.innerHTML = '<p>Buscando servicios...</p>';

    // 1. LLAMAMOS A LAS 3 APIS EN PARALELO
    // Promise.all() ejecuta todas las promesas (peticiones) al mismo tiempo.
    // Espera a que todas terminen.
    try {
      const [resultadosVuelos, resultadosHoteles, resultadosBuses] = await Promise.all([
        llamarApiVuelos(),
        llamarApiHoteles(),
        llamarApiBuses()
      ]);

      // 2. COMBINAMOS LOS RESULTADOS
      // Usamos el "spread operator" (...) para juntar los 3 arrays en uno solo
      const todosLosResultados = [...resultadosVuelos, ...resultadosHoteles, ...resultadosBuses];

      // 3. MOSTRAMOS TODO
      mostrarResultados(todosLosResultados);

    } catch (error) {
      // Este error solo saltará si una de las APIs falla de forma crítica
      console.error("Error general al consultar APIs:", error);
      resultadosContainer.innerHTML = `<p style="color: red;">Error general al conectar con los servicios. Intenta de nuevo.</p>`;
    }
  });

  // --- NUESTRAS 3 FUNCIONES DE API ---

  async function llamarApiVuelos() {
    // CAMBIO: Ya no apuntamos a localhost:3000
    const API_URL = '/api/vuelos';
    try {
      const response = await fetch(API_URL);
      // ...el resto de la función es idéntica...
      if (!response.ok) throw new Error('Error en API Vuelos');
      const data = await response.json();
      console.log("Datos recibidos de Vuelos:", data);
      return data;
    } catch (error) {
      console.error("Falló la conexión con la API de Vuelos:", error);
      return [];
    }
  }

  async function llamarApiHoteles() {
    // CAMBIO:
    const API_URL = '/api/hoteles';
    try {
      const response = await fetch(API_URL);
      // ...el resto es idéntico...
      if (!response.ok) throw new Error('Error en API Hoteles');
      const data = await response.json();
      console.log("Datos recibidos de Hoteles:", data);
      return data;
    } catch (error) {
      console.error("Falló la conexión con la API de Hoteles:", error);
      return [];
    }
  }

  async function llamarApiBuses() {
    // CAMBIO:
    const API_URL = '/api/buses';
    try {
      const response = await fetch(API_URL);
      // ...el resto es idéntico...
      if (!response.ok) throw new Error('Error en API Buses');
      const data = await response.json();
      console.log("Datos recibidos de Buses:", data);
      return data;
    } catch (error) {
      console.error("Falló la conexión con la API de Buses:", error);
      return [];
    }
  }


  /**
   * Esta función es la MISMA de antes.
   * No necesita cambiar, ya que solo se dedica a "pintar"
   * cualquier array de resultados que reciba.
   */
  function mostrarResultados(resultados) {
    resultadosContainer.innerHTML = '';

    if (resultados.length === 0) {
      resultadosContainer.innerHTML = '<p>No se encontraron servicios para esta búsqueda.</p>';
      return;
    }

    resultados.forEach(item => {

      // 1. LÓGICA PARA HOTELES: Selector de Personas
      let selectorPersonasHTML = '';
      if (item.tipo.includes('Hotel')) {
        selectorPersonasHTML = `
          <label style="margin-top: 10px; font-size: 0.9em;">
            Personas (Máx. ${item.max_personas || 2}):
            <input type="number" min="1" max="${item.max_personas || 2}" value="1" style="margin-bottom: 0;">
          </label>
        `;
      }

      // 2. LÓGICA PARA HOTELES: Selector de Fechas (¡ESTO ES LO QUE FALTABA!)
      // Agregamos las clases 'fecha-inicio' y 'fecha-fin' que busca tu función reservar
      let inputsFechasHTML = '';
      if (item.tipo.includes('Hotel')) {
        inputsFechasHTML = `
           <div class="grid" style="margin-top: 10px;">
             <label>
               Desde:
               <input type="date" class="fecha-inicio" required>
             </label>
             <label>
               Hasta:
               <input type="date" class="fecha-fin" required>
             </label>
           </div>
        `;
      }

      const itemHTML = `
        <article>
          <img src="${item.imagen}" alt="${item.tipo} ${item.servicio}" style="width: 100%; height: 200px; object-fit: cover; margin-bottom: 1rem; border-radius: var(--border-radius);" loading="lazy">
          <header>
            <small style="color: gray; text-transform: uppercase; font-size: 0.7em;">
                Ofrecido por: <strong>${item.nombre_agencia || 'Agencia KIS'}</strong>
            </small>
            <br>
            <strong>${item.tipo} - ${item.servicio}</strong>
          </header>
          
          <p>${item.descripcion}</p>
          <p><em>Horario: ${item.horario}</em></p>
          
          <p><small>Disponibles: ${item.stock}</small></p>

          ${selectorPersonasHTML}
          ${inputsFechasHTML}
          
          <footer style="display: flex; align-items: center; justify-content: space-between;">
            <strong>Precio: $${item.precio.toFixed(2)} MXN</strong>
            
            <button 
                style="float: right;" 
                onclick="reservar('${item.tipo}', ${item.id}, '${item.servicio}', this)">
              Reservar
            </button>
          </footer>
        </article>
      `;
      resultadosContainer.innerHTML += itemHTML;
    });
  }
});

// Función global para reservar
async function reservar(tipoRaw, id, nombreServicio, btnElement) {
  const usuarioGuardado = localStorage.getItem('usuario_agencia');
  if (!usuarioGuardado) {
    alert("Debes iniciar sesión para reservar");
    window.location.href = "login.html";
    return;
  }
  const usuario = JSON.parse(usuarioGuardado);

  // LÓGICA DE FECHAS (Punto 4: Rango de fechas para Hoteles)
  let detallesExtra = "";
  if (tipoRaw.includes('Hotel')) {
    // Buscamos los inputs dentro de la misma tarjeta (<article>) del botón presionado
    const article = btnElement.closest('article');
    const inicio = article.querySelector('.fecha-inicio').value;
    const fin = article.querySelector('.fecha-fin').value;

    if (!inicio || !fin) {
      alert("Por favor selecciona las fechas de entrada y salida.");
      return;
    }
    if (inicio > fin) {
      alert("La fecha de salida no puede ser antes de la entrada.");
      return;
    }
    detallesExtra = ` (Del ${inicio} al ${fin})`;
  }

  // Normalizar tipo para el backend ('vuelo', 'hotel', 'bus')
  let tipoBackend = 'vuelo';
  if (tipoRaw.includes('Hotel')) tipoBackend = 'hotel';
  if (tipoRaw.includes('Autobús') || tipoRaw.includes('Bus')) tipoBackend = 'bus';

  const detalles = `${tipoRaw}: ${nombreServicio}${detallesExtra}`;

  if (!confirm(`¿Confirmar reserva de: ${detalles}?`)) return;

  try {
    const res = await fetch('/api/agencia/reservas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: usuario.email,
        tipo_servicio: tipoBackend,
        id_servicio: id,
        detalles: detalles
      })
    });

    const data = await res.json();

    if (res.ok) {
      alert("¡Reserva exitosa! Se ha descontado de nuestro inventario.");
      // Recargamos la búsqueda para que el usuario vea que el stock bajó
      document.getElementById('form-busqueda').dispatchEvent(new Event('submit'));
    } else {
      alert("Error: " + (data.error || "No se pudo reservar"));
    }
  } catch (e) { console.error(e); alert("Error de conexión"); }
}

async function probarSeguridadReserva() {
    // 1. Obtener el JWT guardado
    const jwt = localStorage.getItem('jwt_token');
    if (!jwt) {
        alert("Debes iniciar sesión primero");
        return;
    }

    // 2. Obtener el Token CSRF del servidor
    const resCsrf = await fetch('/api/agencia/csrf-token');
    const dataCsrf = await resCsrf.json();
    const csrfToken = dataCsrf.csrf_token;

    // 3. Hacer la petición POST protegida
    try {
        const response = await fetch('/api/agencia/reservas', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${jwt}`,     // <-- Escudo 1: Identidad
                'X-CSRFToken': csrfToken              // <-- Escudo 2: Protección CSRF
            },
            body: JSON.stringify({ vuelo_id: 101, destino: "Cancún" })
        });

        const data = await response.json();
        if (response.ok) {
            alert("Éxito: " + data.mensaje);
        } else {
            alert("Error de seguridad: " + data.error);
        }
    } catch (error) {
        console.error("Error en la petición:", error);
    }
}