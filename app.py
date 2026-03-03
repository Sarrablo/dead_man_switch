from flask import Flask, render_template, request, redirect, flash, url_for
import mysql.connector
import uuid
from datetime import date
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))

# Configuración de la base de datos desde variables de entorno
db_config = {
    "host": os.getenv('DB_HOST'),
    "port": int(os.getenv('DB_PORT', 3306)),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "database": os.getenv('DB_NAME')
}

# Configuración SMTP desde variables de entorno
SMTP_CONFIG = {
    "server": os.getenv('SMTP_SERVER'),
    "port": int(os.getenv('SMTP_PORT', 465)),
    "user": os.getenv('SMTP_USER'),
    "password": os.getenv('SMTP_PASSWORD')
}

# Contraseña para securizar los endpoints
ENDPOINT_PASSWORD = os.getenv('ENDPOINT_PASSWORD', 'TuPasswordSeguro123')

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

def send_email(to_address, subject, html_content):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_CONFIG['user']
        msg['To'] = to_address
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))

        # Asegurarse de que el servidor y puerto sean strings/ints correctos
        with smtplib.SMTP_SSL(str(SMTP_CONFIG['server']), int(SMTP_CONFIG['port'])) as server:
            server.login(str(SMTP_CONFIG['user']), str(SMTP_CONFIG['password']))
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create', methods=['POST'])
def create_switch():
    verification_address = request.form.get('verificationAddress')
    mail_address = request.form.get('mailAddress')
    content = request.form.get('content')
    trigger_days = request.form.get('triggerDays')
    
    internal_identifier = str(uuid.uuid4())
    last_access = date.today()
    active = 1 # Por defecto activo al crear
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO dead_man_switch 
                (internalIdentifier, verificationAddress, mailAddress, content, lastAccess, triggerDays, active) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (internal_identifier, verification_address, mail_address, content, last_access, trigger_days, active)
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            flash(f"Switch creado con éxito. Tu identificador es: {internal_identifier}", "success")
        except mysql.connector.Error as err:
            flash(f"Error al insertar en la base de datos: {err}", "danger")
    else:
        flash("No se pudo conectar a la base de datos.", "danger")
    
    return redirect(url_for('index'))

@app.route('/update_status', methods=['GET'])
def update_status():
    internal_identifier = request.args.get('internalIdentifier')
    active_param = request.args.get('active', 'false')
    
    # Convertir 'true'/'false' a booleano/int para la DB
    active_val = 1 if active_param.lower() == 'true' else 0
    active_text = 'Activo' if active_val == 1 else 'Inactivo'
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = "UPDATE dead_man_switch SET active = %s WHERE internalIdentifier = %s"
            cursor.execute(query, (active_val, internal_identifier))
            conn.commit()
            
            # Verificar si se actualizó algo
            if cursor.rowcount == 0:
                cursor.close()
                conn.close()
                return render_template('status.html', title="No encontrado", message=f"No se encontró ningún switch con el identificador: {internal_identifier}", category="error")
            
            cursor.close()
            conn.close()
            return render_template('status.html', title="Estado Actualizado", message=f"El switch {internal_identifier} ahora está: {active_text}", category="success")
        except mysql.connector.Error as err:
            return render_template('status.html', title="Error de Base de Datos", message=str(err), category="error")
    else:
        return render_template('status.html', title="Error de Conexión", message="No se pudo conectar a la base de datos.", category="error")

@app.route('/verify', methods=['GET'])
def verify():
    internal_identifier = request.args.get('internalIdentifier')
    today = date.today()
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            # Primero buscamos el registro para comprobar la fecha
            query_select = "SELECT lastAccess FROM dead_man_switch WHERE internalIdentifier = %s"
            cursor.execute(query_select, (internal_identifier,))
            record = cursor.fetchone()
            
            if not record:
                cursor.close()
                conn.close()
                return render_template('status.html', title="No encontrado", message=f"No se encontró ningún switch con el identificador: {internal_identifier}", category="error")
            
            # Comprobamos si ya se ha verificado hoy
            if record['lastAccess'] == today:
                cursor.close()
                conn.close()
                return render_template('status.html', title="Ya Verificado", message=f"El switch {internal_identifier} ya ha sido verificado hoy ({today}). No es necesario hacerlo de nuevo.", category="success")
            
            # Si no se ha verificado hoy, actualizamos
            query_update = "UPDATE dead_man_switch SET lastAccess = %s WHERE internalIdentifier = %s"
            cursor.execute(query_update, (today, internal_identifier))
            conn.commit()
            
            cursor.close()
            conn.close()
            return render_template('status.html', title="Acceso Verificado", message=f"Fecha de último acceso actualizada a {today} para el switch: {internal_identifier}", category="success")
        except mysql.connector.Error as err:
            return render_template('status.html', title="Error de Base de Datos", message=str(err), category="error")
    else:
        return render_template('status.html', title="Error de Conexión", message="No se pudo conectar a la base de datos.", category="error")

@app.route('/edit', methods=['GET'])
def edit_view():
    internal_identifier = request.args.get('internalIdentifier')
    if not internal_identifier:
        return render_template('status.html', title="Error", message="Falta el identificador interno.", category="error")
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM dead_man_switch WHERE internalIdentifier = %s"
            cursor.execute(query, (internal_identifier,))
            switch = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not switch:
                return render_template('status.html', title="No encontrado", message=f"No se encontró ningún switch con el identificador: {internal_identifier}", category="error")
            
            return render_template('edit.html', switch=switch)
        except mysql.connector.Error as err:
            return render_template('status.html', title="Error de Base de Datos", message=str(err), category="error")
    else:
        return render_template('status.html', title="Error de Conexión", message="No se pudo conectar a la base de datos.", category="error")

@app.route('/modify', methods=['POST'])
def modify_switch():
    internal_identifier = request.form.get('internalIdentifier')
    verification_address = request.form.get('verificationAddress')
    mail_address = request.form.get('mailAddress')
    content = request.form.get('content')
    trigger_days = request.form.get('triggerDays')
    
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                UPDATE dead_man_switch 
                SET verificationAddress = %s, mailAddress = %s, content = %s, triggerDays = %s
                WHERE internalIdentifier = %s
            """
            cursor.execute(query, (verification_address, mail_address, content, trigger_days, internal_identifier))
            conn.commit()
            
            if cursor.rowcount == 0:
                cursor.close()
                conn.close()
                return render_template('status.html', title="Error", message="No se realizaron cambios o el identificador no existe.", category="error")
            
            cursor.close()
            conn.close()
            return render_template('status.html', title="Cambios Guardados", message=f"Los datos del switch {internal_identifier} han sido actualizados con éxito.", category="success")
        except mysql.connector.Error as err:
            return render_template('status.html', title="Error de Base de Datos", message=str(err), category="error")
    else:
        return render_template('status.html', title="Error de Conexión", message="No se pudo conectar a la base de datos.", category="error")

@app.route('/send_daily_verification', methods=['GET'])
def send_daily_verification():
    password = request.args.get('password')
    if password != ENDPOINT_PASSWORD:
        return render_template('status.html', title="No Autorizado", message="Contraseña de endpoint incorrecta.", category="error")

    conn = get_db_connection()
    if not conn:
        return render_template('status.html', title="Error de Conexión", message="No se pudo conectar a la base de datos.", category="error")

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM dead_man_switch WHERE active = 1"
        cursor.execute(query)
        switches = cursor.fetchall()

        sent_count = 0
        error_count = 0
        base_url = request.host_url.rstrip('/')

        for sw in switches:
            internal_id = sw['internalIdentifier']
            to_email = sw['verificationAddress']
            
            verify_url = f"{base_url}/verify?internalIdentifier={internal_id}"
            deactivate_url = f"{base_url}/update_status?internalIdentifier={internal_id}&active=false"

            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                    <h2 style="color: #6366f1;">Verificación de Dead Man Switch</h2>
                    <p>Hola,</p>
                    <p>Este es un recordatorio diario para verificar que sigues activo y evitar que tu Dead Man Switch se dispare.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{verify_url}" style="background-color: #6366f1; color: white; padding: 15px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">VERIFICAR ESTADO</a>
                    </div>
                    <p>Si el botón anterior no funciona, copia y pega la siguiente URL en tu navegador:</p>
                    <p style="word-break: break-all;"><a href="{verify_url}">{verify_url}</a></p>
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="font-size: 0.9em; color: #666;">
                        <strong>¿Quieres desactivar el switch?</strong><br>
                        Si ya no necesitas este switch de seguridad, puedes desactivarlo haciendo clic aquí:<br>
                        <a href="{deactivate_url}" style="color: #ef4444;">Desactivar Switch</a>
                    </p>
                    
                    <p style="font-size: 0.8em; color: #999; margin-top: 30px;">
                        Para desuscribirse de forma manual correo: <a href="mailto:unsubscribe@example.com">unsubscribe@example.com</a><br>
                        Para reportar abusos: <a href="mailto:abuse@example.com">abuse@example.com</a>
                    </p>
                </div>
            </body>
            </html>
            """
            
            if send_email(to_email, "Recordatorio: Verifica tu Dead Man Switch", html_content):
                sent_count += 1
            else:
                error_count += 1

        cursor.close()
        conn.close()
        return render_template('status.html', title="Proceso Completado", message=f"Se han enviado {sent_count} correos con éxito. Errores: {error_count}.", category="success")
    except mysql.connector.Error as err:
        return render_template('status.html', title="Error de Base de Datos", message=str(err), category="error")

@app.route('/trigger_switches', methods=['GET'])
def trigger_switches():
    password = request.args.get('password')
    if password != ENDPOINT_PASSWORD:
        return render_template('status.html', title="No Autorizado", message="Contraseña de endpoint incorrecta.", category="error")

    conn = get_db_connection()
    if not conn:
        return render_template('status.html', title="Error de Conexión", message="No se pudo conectar a la base de datos.", category="error")

    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT * FROM dead_man_switch WHERE active = 1"
        cursor.execute(query)
        switches = cursor.fetchall()

        triggered_results = []
        today = date.today()

        for sw in switches:
            internal_id = sw['internalIdentifier']
            last_access = sw['lastAccess']
            trigger_days = sw['triggerDays']
            days_passed = (today - last_access).days
            
            if days_passed > trigger_days:
                mail_addresses = [email.strip() for email in sw['mailAddress'].split(',')]
                content = sw['content']
                subject = f"MENSAJE DE EMERGENCIA: Dead Man Switch de {sw['verificationAddress']}"
                html_content = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 2px solid #ef4444; border-radius: 10px;">
                        <h2 style="color: #ef4444;">Mensaje de Emergencia Automático</h2>
                        <p>Este correo ha sido enviado automáticamente porque el <strong>Dead Man Switch</strong> asociado a <em>{sw['verificationAddress']}</em> no ha sido verificado en los últimos {trigger_days} días.</p>
                        <div style="background-color: #f8fafc; padding: 20px; border-radius: 5px; border-left: 4px solid #6366f1; margin: 20px 0;">
                            <h3 style="margin-top: 0; color: #1e293b;">Contenido del mensaje:</h3>
                            <p style="white-space: pre-wrap;">{content}</p>
                        </div>
                        <p style="font-size: 0.8em; color: #999; margin-top: 30px;">
                            Este es un sistema automatizado. Por favor, no respondas a este correo.<br>
                            Reportar abusos: <a href="mailto:abuse@example.com">abuse@example.com</a>
                        </p>
                    </div>
                </body>
                </html>
                """
                emails_sent_to = []
                for email in mail_addresses:
                    if send_email(email, subject, html_content):
                        emails_sent_to.append(email)
                
                update_query = "UPDATE dead_man_switch SET active = 0 WHERE internalIdentifier = %s"
                cursor.execute(update_query, (internal_id,))
                conn.commit()
                triggered_results.append({"id": internal_id, "emails": emails_sent_to})

        cursor.close()
        conn.close()
        
        if not triggered_results:
            return render_template('status.html', title="Proceso Finalizado", message="No hay switches que cumplan las condiciones para ser disparados hoy.", category="success")
        
        details = "<br>".join([f"• <strong>{res['id']}</strong> enviado a: {', '.join(res['emails'])}" for res in triggered_results])
        return render_template('status.html', title="Switches Disparados", message=f"Se han procesado los siguientes switches:<br><br>{details}", category="success")
    except mysql.connector.Error as err:
        return render_template('status.html', title="Error de Base de Datos", message=str(err), category="error")

if __name__ == '__main__':
    app.run(debug=True, port=5000)
