/* ==========================================
   STACKPP DASHBOARD
   ========================================== */

const email =
    localStorage.getItem(
        'user_email'
    );

const tgUser =
    localStorage.getItem(
        'tg_user'
    );

/* ==========================================
   PROTECCION DE RUTA
   ========================================== */

if (!email || !tgUser) {

    window.location.replace(
        'index.html'
    );

}

/* ==========================================
   ELEMENTOS
   ========================================== */

const metaUser =
    document.getElementById(
        'meta-user'
    );

const tgAccount =
    document.getElementById(
        'tg-account'
    );

const statLinks =
    document.getElementById(
        'stat-links'
    );

const statFiles =
    document.getElementById(
        'stat-files'
    );

const apiStatus =
    document.getElementById(
        'api-status'
    );

const welcomeTitle =
    document.getElementById(
        'welcome-title'
    );

/* ==========================================
   INFORMACION BASICA
   ========================================== */

metaUser.innerText = email;

tgAccount.innerText = tgUser;

/* ==========================================
   CONSULTAR METRICAS
   ========================================== */

async function consultarMetricas() {

    try {

        const response =
            await fetch(
                `${window.location.origin}/api/metricas?email=${email}`
            );

        const data =
            await response.json();

        if (
            data.status === 'ok'
        ) {

            statLinks.innerText =
                data.links_procesados ?? 0;

            statFiles.innerText =
                data.archivos_procesados ?? 0;

            apiStatus.innerText =
                "Conectado";

            apiStatus.style.color =
                "#10b981";

            return;
        }

        apiStatus.innerText =
            "Respuesta inválida";

        apiStatus.style.color =
            "#ef4444";

    } catch (error) {

        console.error(error);

        apiStatus.innerText =
            "Sin conexión";

        apiStatus.style.color =
            "#ef4444";

        welcomeTitle.innerText =
            "Servidor no disponible";

    }

}

/* ==========================================
   LOGOUT
   ========================================== */

function logout() {

    localStorage.removeItem(
        'user_email'
    );

    localStorage.removeItem(
        'user_realname'
    );

    localStorage.removeItem(
        'tg_user'
    );

    window.location.replace(
        'index.html'
    );

}

/* ==========================================
   AUTO REFRESH
   ========================================== */

consultarMetricas();

setInterval(
    consultarMetricas,
    10000
);

/* ==========================================
   EVENTOS
   ========================================== */

document
    .getElementById(
        'btn-logout'
    )
    .addEventListener(
        'click',
        logout
    );