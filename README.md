# Dead Man Switch Project 🛡️

Este proyecto es una aplicación web basada en Flask que implementa un sistema de **"Interruptor de hombre muerto" (Dead Man Switch)**. Su propósito es permitir a los usuarios almacenar contenido que será enviado automáticamente a contactos de emergencia si el usuario no verifica su estado de actividad durante un periodo determinado.

## ✨ Características

-   **Interfaz Moderna**: Diseño premium y oscuro utilizando Bootstrap 5 e Inter Font.
-   **Gestión de Switches**: Crea, edita y desactiva switches de seguridad de forma sencilla.
-   **Verificación Diaria**: Sistema de recordatorios por correo electrónico para mantener el switch reiniciado.
-   **Disparo Automático**: Si el tiempo de inactividad supera el límite configurado, el contenido secreto se envía a las direcciones de correo especificadas.
-   **Seguridad**:
    -   Uso de variables de entorno para proteger credenciales sensibles.
    -   Endpoints administrativos protegidos por contraseña.
    -   Generación de identificadores únicos (UUID4).

## 🚀 Instalación y Configuración

### 1. Clonar el repositorio
```bash
git clone <tu-url-de-github>
cd dead_man_switch
```

### 2. Configurar el entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
# venv\Scripts\activate   # En Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Copia el archivo `.env.example` a un nuevo archivo llamado `.env` y rellena tus datos reales:
```bash
cp .env.example .env
```

Variables requeridas en `.env`:
-   `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: Credenciales de tu base de datos MariaDB.
-   `SMTP_SERVER`, `SMTP_USER`, `SMTP_PASSWORD`: Configuración para el envío de correos.
-   `ENDPOINT_PASSWORD`: Contraseña para autorizar el envío manual de correos y procesos de disparo.

## 🐳 Ejecución con Docker (Recomendado)

Si tienes Docker y Docker Compose instalados, puedes levantar la aplicación simplemente con:

```bash
docker-compose up -d --build
```

La aplicación estará disponible en `http://localhost:5000`.

### 5. Preparar la Base de Datos manualmente (si no usas Docker)
...
Asegúrate de tener creada la tabla en tu MariaDB:
```sql
CREATE TABLE `dead_man_switch` (
  `idSwitch` int(11) NOT NULL AUTO_INCREMENT,
  `internalIdentifier` text NOT NULL,
  `verificationAddress` text NOT NULL,
  `mailAddress` text NOT NULL,
  `content` text NOT NULL,
  `lastAccess` date NOT NULL,
  `triggerDays` int(11) NOT NULL,
  `active` tinyint(1) NOT NULL,
  PRIMARY KEY (`idSwitch`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
```

## 🛠️ Uso de Endpoints

| Endpoint | Descripción |
| :--- | :--- |
| `/` | Landing page para crear un nuevo switch. |
| `/edit?internalIdentifier=UUID` | Formulario para modificar un switch existente. |
| `/verify?internalIdentifier=UUID` | Reinicia el contador de inactividad. |
| `/send_daily_verification?password=...` | Envía recordatorios de verificación a todos los usuarios activos. |
| `/trigger_switches?password=...` | Comprueba switches expirados y envía el contenido a los contactos. |

## 📧 Contacto y Abuso
El sistema incluye direcciones configurables para desuscripción manual y reportes de abuso.

---
Desarrollado con Flask y Bootstrap 5.
