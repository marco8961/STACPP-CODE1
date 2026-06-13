/* ==========================================
   STACKPP LOGIN & AUTHENTICATION
   ========================================== */

const API_URL = window.location.origin;

let userData = {};

/* ==========================================
   HELPERS & MENSAJES
   ========================================== */

function showMsg(text, isError = false) {
    const el = document.getElementById('status-msg');
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
}

function setButtonLoading(button, loadingText) {
    button.dataset.originalText = button.innerText;
    button.disabled = true;
    button.innerText = loadingText;
}

function resetButton(button) {
    button.disabled = false;
    if (button.dataset.originalText) {
        button.innerText = button.dataset.originalText;
    }
}

/* ==========================================
   TOGGLE ENTRE USUARIO Y ADMINISTRADOR
   ========================================== */

const wrapperGoogle = document.getElementById('wrapper-google');
const wrapperAdmin = document.getElementById('wrapper-admin-login');
const statusMsg = document.getElementById('status-msg');

document.getElementById('link-show-admin').addEventListener('click', (e) => {
    e.preventDefault();
    wrapperGoogle.style.display = 'none';
    wrapperAdmin.style.display = 'block';
    statusMsg.style.display = 'none';
});

document.getElementById('link-show-user').addEventListener('click', (e) => {
    e.preventDefault();
    wrapperAdmin.style.display = 'none';
    wrapperGoogle.style.display = 'block';
    statusMsg.style.display = 'none';
});

/* ==========================================
   INICIO DE SESIÓN DE ADMINISTRADORES
   ========================================== */

async function loginAdministrador(e) {
    const btn = document.getElementById('btn-admin-login');
    const email = document.getElementById('admin-email').value.trim();
    const password = document.getElementById('admin-password').value;

    if (!email || !password) {
        showMsg("Ingresa tu correo y contraseña.", true);
        return;
    }

    try {
        setButtonLoading(btn, "Autenticando...");
        showMsg("Validando credenciales...");

        const response = await fetch(`${API_URL}/auth/admin_login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            localStorage.setItem('user_email', data.email);
            localStorage.setItem('user_realname', 'Administrador');
            localStorage.setItem('user_role', 'admin');

            showMsg("Inicio de sesión exitoso. Cargando SOC...");

            setTimeout(() => {
                window.location.replace('admin.html');
            }, 1000);
        } else {
            showMsg(data.detail || "Credenciales incorrectas.", true);
        }
    } catch (error) {
        console.error("Error al iniciar sesión de admin:", error);
        showMsg("Error de conexión con el servidor.", true);
    } finally {
        resetButton(btn);
    }
}

document.getElementById('admin-login-form').addEventListener('submit', loginAdministrador);

/* ==========================================
   GOOGLE LOGIN (USUARIOS ESTÁNDAR)
   ========================================== */

async function handleCredentialResponse(response) {
    try {
        showMsg('Verificando cuenta de Google...');

        const loginRes = await fetch(`${API_URL}/auth/google_login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                credential: response.credential
            })
        });

        if (!loginRes.ok) {
            throw new Error('Error en autenticación de Google');
        }

        const loginData = await loginRes.json();

        localStorage.setItem('user_email', loginData.email);
        localStorage.setItem('user_realname', loginData.name);
        localStorage.setItem('user_role', loginData.role);

        // Si es administrador (iniciando accidentalmente por Google)
        if (loginData.role === 'admin') {
            showMsg('Acceso de Administrador verificado. Redirigiendo...');
            setTimeout(() => {
                window.location.replace('admin.html');
            }, 1000);
            return;
        }

        // Si es usuario estándar, verificar si ya vinculó Telegram
        const checkRes = await fetch(`${API_URL}/auth/check_user`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: loginData.email
            })
        });

        const checkData = await checkRes.json();

        if (checkData.telegram_linked === true) {
            localStorage.setItem('tg_user', checkData.user);
            showMsg('Sesión encontrada. Redirigiendo...');
            setTimeout(() => {
                window.location.replace('dashboard.html');
            }, 1000);
            return;
        }

        // Mostrar formulario de Telegram si no está enlazado
        document.getElementById('wrapper-google').style.display = 'none';
        document.getElementById('wrapper-telegram').style.display = 'block';
        document.getElementById('google-welcome').innerText =
            `Bienvenido ${loginData.name}. Vincula tu cuenta de Telegram para activar el escudo.`;

    } catch (error) {
        console.error(error);
        showMsg('Error al procesar el inicio de sesión.', true);
    }
}

/* ==========================================
   VINCULACIÓN DE TELEGRAM (SOLICITAR CÓDIGO)
   ========================================== */

async function solicitarCodigo() {
    const phone = document.getElementById('phone').value.trim();
    const btn = document.getElementById('btn-send-code');

    if (!phone) {
        showMsg('Introduce tu número de teléfono de Telegram.', true);
        return;
    }

    const phoneRegex = /^\+\d{8,15}$/;
    if (!phoneRegex.test(phone)) {
        showMsg('Formato inválido. Ejemplo: +51987654321', true);
        return;
    }

    try {
        setButtonLoading(btn, 'Enviando...');
        showMsg('Enviando código de acceso...');

        const res = await fetch(`${API_URL}/auth/solicitar_codigo`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                phone,
                email: localStorage.getItem('user_email')
            })
        });

        const data = await res.json();

        if (data.status === 'ok') {
            document.getElementById('step-phone').style.display = 'none';
            document.getElementById('step-verify').style.display = 'block';
            showMsg('Código de verificación enviado a tu aplicación de Telegram.');
        } else {
            showMsg(data.msg || 'Error al solicitar el código.', true);
        }
    } catch (err) {
        console.error(err);
        showMsg('Error de conexión con el servidor.', true);
    } finally {
        resetButton(btn);
    }
}

/* ==========================================
   VINCULACIÓN DE TELEGRAM (VERIFICAR CÓDIGO)
   ========================================== */

async function verificarCodigo() {
    const phone = document.getElementById('phone').value.trim();
    const code = document.getElementById('code').value.trim();
    const password = document.getElementById('password').value.trim();
    const btn = document.getElementById('btn-verify');

    if (!code) {
        showMsg('Introduce el código de verificación recibido.', true);
        return;
    }

    try {
        setButtonLoading(btn, 'Validando...');

        const res = await fetch(`${API_URL}/auth/verificar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                phone,
                code,
                password,
                email: localStorage.getItem('user_email')
            })
        });

        const data = await res.json();

        if (data.status === 'requires_password') {
            document.getElementById('wrapper-pwd').style.display = 'block';
            showMsg('Tu cuenta de Telegram tiene activada la verificación en dos pasos (2FA). Ingresa tu contraseña de Telegram.', true);
            return;
        }

        if (data.status === 'success') {
            localStorage.setItem('tg_user', data.user);
            showMsg('¡Escudo de protección sincronizado correctamente!');
            setTimeout(() => {
                window.location.replace('dashboard.html');
            }, 1200);
            return;
        }

        showMsg(data.msg || 'El código introducido no es válido.', true);

    } catch (err) {
        console.error(err);
        showMsg('Error de conexión con el servidor.', true);
    } finally {
        resetButton(btn);
    }
}

/* ==========================================
   EVENTOS
   ========================================== */

document.getElementById('btn-send-code').addEventListener('click', solicitarCodigo);
document.getElementById('btn-verify').addEventListener('click', verificarCodigo);
window.handleCredentialResponse = handleCredentialResponse;