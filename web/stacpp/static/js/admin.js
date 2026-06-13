/* ==========================================
   STACKPP ADMIN PORTAL
   ========================================== */

const API_URL = window.location.origin;

// Verificar que sea admin al cargar
const userRole = localStorage.getItem('user_role');
const userEmail = localStorage.getItem('user_email');

if (userRole !== 'admin' || !userEmail) {
    window.location.replace('login.html');
}

// Mostrar correo del admin
document.getElementById('admin-email-display').innerText = userEmail;

/* ==========================================
   HELPERS & COMUNICACIÓN CON API
   ========================================== */

async function fetchSecure(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (response.status === 401 || response.status === 403) {
            // Sesión expirada o no autorizado
            logout();
            return null;
        }
        return response;
    } catch (error) {
        console.error("Error de conexión:", error);
        return null;
    }
}

/* ==========================================
   CARGA DE DATOS DEL SOC
   ========================================== */

async function cargarMetricasGlobales() {
    const res = await fetchSecure(`${API_URL}/api/admin/metricas_globales`);
    if (!res) return;

    const data = await res.json();
    if (data.status === 'ok') {
        document.getElementById('stat-total-users').innerText = data.total_usuarios ?? 0;
        document.getElementById('stat-total-links').innerText = data.total_links ?? 0;
        document.getElementById('stat-total-threats').innerText = data.total_malware ?? 0;
    }
}

async function cargarUsuarios() {
    const res = await fetchSecure(`${API_URL}/api/admin/usuarios`);
    if (!res) return;

    const data = await res.json();
    const tbody = document.getElementById('users-table-body');
    tbody.innerHTML = '';

    if (data.status === 'ok' && data.usuarios.length > 0) {
        data.usuarios.forEach(user => {
            const tr = document.createElement('tr');
            
            // Badge para el estado
            const isActive = user.status === 'Activo';
            const badgeBg = isActive ? 'rgba(16,185,129,.08)' : 'rgba(244,63,94,.08)';
            const textColor = isActive ? '#10b981' : '#f43f5e';
            const borderStyle = isActive ? '1px solid rgba(16,185,129,.2)' : '1px solid rgba(244,63,94,.2)';

            tr.innerHTML = `
                <td data-label="Nombre"><strong>${escapeHTML(user.nombre)}</strong></td>
                <td data-label="Telegram ID" style="color: var(--muted); font-family: 'Fira Code', monospace; font-size: 0.85rem;">${escapeHTML(user.telegram_id.toString())}</td>
                <td data-label="Teléfono">${escapeHTML(user.telefono)}</td>
                <td data-label="Email">${escapeHTML(user.email)}</td>
                <td data-label="Estado Escudo">
                    <span style="padding: 4px 10px; border-radius: 999px; background: ${badgeBg}; color: ${textColor}; border: ${borderStyle}; font-size: 0.8rem; font-weight: 700; display: inline-block;">
                        ${user.status}
                    </span>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } else {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="padding: 20px; text-align: center; color: var(--muted);">No hay usuarios registrados.</td>
            </tr>
        `;
    }
}

async function cargarAlertas() {
    const res = await fetchSecure(`${API_URL}/api/admin/alertas`);
    if (!res) return;

    const data = await res.json();
    const tbody = document.getElementById('threats-table-body');
    tbody.innerHTML = '';

    if (data.status === 'ok' && data.alertas.length > 0) {
        data.alertas.forEach(alerta => {
            const tr = document.createElement('tr');
            
            // Formatear tipo
            const isMalware = alerta.tipo === 'Malware';
            const badgeBg = isMalware ? 'rgba(244, 63, 94, 0.08)' : 'rgba(245, 158, 11, 0.08)';
            const badgeColor = isMalware ? '#f43f5e' : '#f59e0b';
            const borderStyle = isMalware ? '1px solid rgba(244, 63, 94, 0.2)' : '1px solid rgba(245, 158, 11, 0.2)';
            
            // Formatear fecha
            const fechaStr = new Date(alerta.fecha).toLocaleString('es-ES', {
                hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit'
            });

            tr.innerHTML = `
                <td data-label="Tipo">
                    <span style="padding: 4px 10px; border-radius: 999px; background: ${badgeBg}; color: ${badgeColor}; border: ${borderStyle}; font-size: 0.8rem; font-weight: 700; display: inline-block;">
                        ${alerta.tipo}
                    </span>
                </td>
                <td data-label="Fecha" style="color: var(--muted); font-size: 0.85rem;">${fechaStr}</td>
                <td data-label="Detalle"><code style="color: #06b6d4; font-family: 'Fira Code', monospace; font-size: 0.85rem;">${escapeHTML(alerta.detalle)}</code></td>
                <td data-label="Mensaje" style="color: var(--muted); font-style: italic; font-size: 0.9rem;">
                    "${escapeHTML(alerta.texto)}"
                </td>
            `;
            tbody.appendChild(tr);
        });
    } else {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="padding: 20px; text-align: center; color: var(--muted);">No se han detectado amenazas recientes.</td>
            </tr>
        `;
    }
}

/* ==========================================
   REGISTRAR NUEVO ADMINISTRADOR
   ========================================== */

async function registrarAdministrador() {
    const emailInput = document.getElementById('new-admin-email');
    const passwordInput = document.getElementById('new-admin-password');
    const msgDiv = document.getElementById('admin-status-msg');
    
    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
        showFeedback(msgDiv, "Introduce correo y contraseña.", true);
        return;
    }

    try {
        const res = await fetchSecure(`${API_URL}/api/admin/crear_administrador`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        if (!res) return;

        const data = await res.json();
        if (data.status === 'ok') {
            showFeedback(msgDiv, data.msg, false);
            emailInput.value = '';
            passwordInput.value = '';
        } else {
            throw new Error(data.msg || 'Error al registrar administrador');
        }
    } catch (error) {
        showFeedback(msgDiv, error.message, true);
    }
}

function showFeedback(el, text, isError) {
    el.innerText = text;
    el.style.display = 'block';
    
    if (isError) {
        el.className = 'status-error';
        el.style.color = '#fb7185';
        el.style.background = 'rgba(244, 63, 94, 0.06)';
        el.style.border = '1px solid rgba(244, 63, 94, 0.2)';
    } else {
        el.className = 'status-success';
        el.style.color = '#34d399';
        el.style.background = 'rgba(16, 185, 129, 0.06)';
        el.style.border = '1px solid rgba(16, 185, 129, 0.2)';
    }

    setTimeout(() => {
        el.style.display = 'none';
    }, 5000);
}

/* ==========================================
   SEGURIDAD & UTILS
   ========================================== */

function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

function logout() {
    localStorage.removeItem('user_email');
    localStorage.removeItem('user_realname');
    localStorage.removeItem('user_role');
    localStorage.removeItem('tg_user');
    
    document.cookie = "session_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
    window.location.replace('login.html');
}

/* ==========================================
   INICIALIZACIÓN
   ========================================== */

function inicializar() {
    cargarMetricasGlobales();
    cargarUsuarios();
    cargarAlertas();

    const interval = setInterval(() => {
        cargarMetricasGlobales();
        cargarUsuarios();
        cargarAlertas();
    }, 15000);

    window.addEventListener('beforeunload', () => clearInterval(interval));
}

// Eventos
document.getElementById('btn-logout').addEventListener('click', logout);
document.getElementById('add-admin-form').addEventListener('submit', registrarAdministrador);

inicializar();
