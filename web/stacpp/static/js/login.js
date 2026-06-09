/* ==========================================
   STACKPP LOGIN
   ========================================== */

const API_URL = window.location.origin;

let userData = {};

/* ==========================================
   HELPERS
   ========================================== */

function showMsg(text, isError = false) {

    const el = document.getElementById('status-msg');

    el.innerText = text;
    el.style.display = 'block';

    if (isError) {
        el.className = 'status-error';
    } else {
        el.className = 'status-success';
    }
}

function setButtonLoading(button, loadingText) {

    button.dataset.originalText =
        button.innerText;

    button.disabled = true;
    button.innerText = loadingText;
}

function resetButton(button) {

    button.disabled = false;

    if (button.dataset.originalText) {
        button.innerText =
            button.dataset.originalText;
    }
}

/* ==========================================
   GOOGLE LOGIN
   ========================================== */

async function handleCredentialResponse(response) {

    try {

        const base64Url =
            response.credential.split('.')[1];

        const base64 =
            base64Url
                .replace(/-/g, '+')
                .replace(/_/g, '/');

        const jsonPayload =
            decodeURIComponent(
                atob(base64)
                    .split('')
                    .map(c =>
                        '%' +
                        ('00' +
                            c.charCodeAt(0)
                                .toString(16)
                        ).slice(-2)
                    )
                    .join('')
            );

        userData =
            JSON.parse(jsonPayload);

        localStorage.setItem(
            'user_email',
            userData.email
        );

        localStorage.setItem(
            'user_realname',
            userData.name
        );

        showMsg(
            'Verificando cuenta...'
        );

        const checkRes = await fetch(
            `${API_URL}/auth/check_user`,
            {
                method: 'POST',
                headers: {
                    'Content-Type':
                        'application/json'
                },
                body: JSON.stringify({
                    email: userData.email
                })
            }
        );

        const checkData =
            await checkRes.json();

        if (
            checkData.telegram_linked === true
        ) {

            localStorage.setItem(
                'tg_user',
                checkData.user
            );

            showMsg(
                'Sesión encontrada. Redirigiendo...'
            );

            setTimeout(() => {

                window.location.replace(
                    'dashboard.html'
                );

            }, 1000);

            return;
        }

        document
            .getElementById(
                'wrapper-google'
            )
            .style.display = 'none';

        document
            .getElementById(
                'wrapper-telegram'
            )
            .style.display = 'block';

        document
            .getElementById(
                'google-welcome'
            )
            .innerText =
            `Bienvenido ${userData.name}. Ahora vincula tu Telegram.`;

    } catch (error) {

        console.error(error);

        showMsg(
            'Error al procesar el inicio de sesión.',
            true
        );
    }
}

/* ==========================================
   RESTAURAR SESION
   ========================================== */

window.addEventListener(
    'load',
    async () => {

        const email =
            localStorage.getItem(
                'user_email'
            );

        if (!email) {
            return;
        }

        try {

            const res = await fetch(
                `${API_URL}/auth/check_user`,
                {
                    method: 'POST',
                    headers: {
                        'Content-Type':
                            'application/json'
                    },
                    body: JSON.stringify({
                        email
                    })
                }
            );

            const data =
                await res.json();

            if (
                data.telegram_linked === true
            ) {

                localStorage.setItem(
                    'tg_user',
                    data.user
                );

                window.location.replace(
                    'dashboard.html'
                );

                return;
            }

        } catch (err) {

            console.error(
                'Error verificando sesión:',
                err
            );
        }
    }
);

/* ==========================================
   SOLICITAR CODIGO
   ========================================== */

async function solicitarCodigo() {

    const phone =
        document
            .getElementById('phone')
            .value
            .trim();

    const btn =
        document.getElementById(
            'btn-send-code'
        );

    if (!phone) {

        showMsg(
            'Introduce tu número.',
            true
        );

        return;
    }

    const phoneRegex =
        /^\+\d{8,15}$/;

    if (!phoneRegex.test(phone)) {

        showMsg(
            'Formato inválido. Ejemplo: +51987654321',
            true
        );

        return;
    }

    try {

        setButtonLoading(
            btn,
            'Enviando...'
        );

        showMsg(
            'Enviando código de acceso...'
        );

        const res = await fetch(
            `${API_URL}/auth/solicitar_codigo`,
            {
                method: 'POST',
                headers: {
                    'Content-Type':
                        'application/json'
                },
                body: JSON.stringify({
                    phone,
                    email:
                        localStorage.getItem(
                            'user_email'
                        )
                })
            }
        );

        const data =
            await res.json();

        if (data.status === 'ok') {

            document
                .getElementById(
                    'step-phone'
                )
                .style.display =
                'none';

            document
                .getElementById(
                    'step-verify'
                )
                .style.display =
                'block';

            showMsg(
                'Código enviado correctamente.'
            );

        } else {

            showMsg(
                data.msg ||
                'Error al solicitar código.',
                true
            );
        }

    } catch (err) {

        console.error(err);

        showMsg(
            'Error de conexión.',
            true
        );

    } finally {

        resetButton(btn);
    }
}

/* ==========================================
   VERIFICAR CODIGO
   ========================================== */

async function verificarCodigo() {

    const phone =
        document
            .getElementById('phone')
            .value
            .trim();

    const code =
        document
            .getElementById('code')
            .value
            .trim();

    const password =
        document
            .getElementById('password')
            .value
            .trim();

    const btn =
        document.getElementById(
            'btn-verify'
        );

    if (!code) {

        showMsg(
            'Introduce el código recibido.',
            true
        );

        return;
    }

    try {

        setButtonLoading(
            btn,
            'Validando...'
        );

        const res = await fetch(
            `${API_URL}/auth/verificar`,
            {
                method: 'POST',
                headers: {
                    'Content-Type':
                        'application/json'
                },
                body: JSON.stringify({
                    phone,
                    code,
                    password,
                    email:
                        localStorage.getItem(
                            'user_email'
                        )
                })
            }
        );

        const data =
            await res.json();

        if (
            data.status ===
            'requires_password'
        ) {

            document
                .getElementById(
                    'wrapper-pwd'
                )
                .style.display =
                'block';

            showMsg(
                'Introduce tu contraseña 2FA.',
                true
            );

            return;
        }

        if (
            data.status ===
            'success'
        ) {

            localStorage.setItem(
                'tg_user',
                data.user
            );

            showMsg(
                'Escudo sincronizado correctamente.'
            );

            setTimeout(() => {

                window.location.replace(
                    'dashboard.html'
                );

            }, 1200);

            return;
        }

        showMsg(
            data.msg ||
            'No fue posible validar el código.',
            true
        );

    } catch (err) {

        console.error(err);

        showMsg(
            'Error de conexión.',
            true
        );

    } finally {

        resetButton(btn);
    }
}

/* ==========================================
   EVENTS
   ========================================== */

document
    .getElementById(
        'btn-send-code'
    )
    .addEventListener(
        'click',
        solicitarCodigo
    );

document
    .getElementById(
        'btn-verify'
    )
    .addEventListener(
        'click',
        verificarCodigo
    );