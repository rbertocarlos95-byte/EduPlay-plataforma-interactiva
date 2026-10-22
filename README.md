# EduPlay · misiones de aprendizaje

Aplicación educativa para aprender con misiones de palabras, ciencia y matemáticas. Incluye registro e inicio de sesión con contraseñas protegidas mediante PBKDF2, perfiles, nivel, XP, racha, misión diaria, insignias y registro persistente de respuestas en SQLite.

## Iniciar

Necesitas Python 3. Ejecuta desde esta carpeta:

```bash
python server.py
```

Abre http://localhost:8000. La base `eduplay.db` se crea automáticamente. No necesita instalar paquetes. Las cuentas y el progreso viven en ese servidor y no se sincronizan entre dispositivos. Para publicar EduPlay en internet, usa alojamiento con HTTPS, respaldos y controles de privacidad adecuados para menores.

## API

- `POST /api/register` — crear cuenta (`name`, `username`, `password`, `avatar`)
- `POST /api/login` — iniciar sesión (`username`, `password`)
- `POST /api/logout` — cerrar sesión (`token`)
- `GET /api/state?token=...` — consultar progreso
- `GET /api/questions` — catálogo de misiones
- `POST /api/answer` — guardar respuesta (`token`, `subject`, `question`, `choice`)

El frontend usa HTML/CSS/JavaScript; el backend usa Python estándar y SQLite.
