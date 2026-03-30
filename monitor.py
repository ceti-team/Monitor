"""
==============================================
  Monitor de Páginas Web con Alertas por Email
  Revisa cambios cada 5 minutos y notifica
==============================================
"""

import hashlib
import smtplib
import time
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup

# ─────────────────────────────────────────────
#   CONFIGURACIÓN — edita estos valores
# ─────────────────────────────────────────────

URL_A_MONITOREAR = "https://sistemamaestro.mineducacion.gov.co/SistemaMaestro/busquedaVacantes.xhtml"   # URL que quieres vigilar
SELECTOR_CSS     = None                    # Opcional: ej. "div.precio" para monitorear
                                           # solo una parte. None = página completa.

INTERVALO_MINUTOS = 5                      # Cada cuántos minutos revisa

# Email remitente (usa Gmail)
EMAIL_ORIGEN      = "mendless42@gmail.com"
EMAIL_PASSWORD    = "jeqe zkwg mkpk usur"  # Contraseña de App de Google (ver README)

# Email destinatario (puede ser el mismo)
EMAIL_DESTINO     = "afcarvajallg@upn.edu.co"

# ─────────────────────────────────────────────
#   NO EDITES DEBAJO DE ESTA LÍNEA
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def obtener_contenido(url: str, selector: str | None) -> str | None:
    """Descarga la página y extrae el contenido relevante."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        if selector:
            elemento = soup.select_one(selector)
            if not elemento:
                log.warning("Selector '%s' no encontró nada en la página.", selector)
                return None
            return elemento.get_text(strip=True)

        # Sin selector: usa todo el texto visible
        for tag in soup(["script", "style", "meta", "noscript"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)

    except requests.RequestException as e:
        log.error("Error al descargar la página: %s", e)
        return None


def calcular_hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def enviar_email(url: str, hash_anterior: str, hash_nuevo: str) -> None:
    """Envía una notificación por email cuando detecta un cambio."""
    ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    asunto = f"🔔 Cambio detectado en {url}"

    cuerpo_html = f"""
    <html><body style="font-family: Arial, sans-serif; color: #333;">
      <h2 style="color: #e74c3c;">⚠️ Cambio detectado</h2>
      <p>El monitor detectó un cambio en la siguiente página:</p>
      <p><a href="{url}">{url}</a></p>
      <table style="border-collapse: collapse; margin-top: 10px;">
        <tr>
          <td style="padding: 6px 12px; background: #f0f0f0;"><strong>Fecha</strong></td>
          <td style="padding: 6px 12px;">{ahora}</td>
        </tr>
        <tr>
          <td style="padding: 6px 12px; background: #f0f0f0;"><strong>Hash anterior</strong></td>
          <td style="padding: 6px 12px; font-family: monospace;">{hash_anterior[:16]}…</td>
        </tr>
        <tr>
          <td style="padding: 6px 12px; background: #f0f0f0;"><strong>Hash nuevo</strong></td>
          <td style="padding: 6px 12px; font-family: monospace;">{hash_nuevo[:16]}…</td>
        </tr>
      </table>
      <p style="margin-top: 20px; font-size: 12px; color: #999;">
        Mensaje automático — Monitor de páginas web
      </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"]    = EMAIL_ORIGEN
    msg["To"]      = EMAIL_DESTINO
    msg.attach(MIMEText(cuerpo_html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ORIGEN, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ORIGEN, EMAIL_DESTINO, msg.as_string())
        log.info("📧 Email de alerta enviado a %s", EMAIL_DESTINO)
    except smtplib.SMTPException as e:
        log.error("Error al enviar el email: %s", e)


def main():
    log.info("🚀 Monitor iniciado")
    log.info("   URL        : %s", URL_A_MONITOREAR)
    log.info("   Selector   : %s", SELECTOR_CSS or "página completa")
    log.info("   Intervalo  : %d minutos", INTERVALO_MINUTOS)

    hash_guardado = None

    while True:
        contenido = obtener_contenido(URL_A_MONITOREAR, SELECTOR_CSS)

        if contenido:
            hash_actual = calcular_hash(contenido)

            if hash_guardado is None:
                hash_guardado = hash_actual
                log.info("✅ Línea base registrada (hash: %s…)", hash_actual[:16])

            elif hash_actual != hash_guardado:
                log.info("🔔 CAMBIO DETECTADO — enviando email...")
                enviar_email(URL_A_MONITOREAR, hash_guardado, hash_actual)
                hash_guardado = hash_actual  # actualiza la referencia

            else:
                log.info("✔  Sin cambios detectados (hash: %s…)", hash_actual[:16])

        time.sleep(INTERVALO_MINUTOS * 60)


if __name__ == "__main__":
    main()
