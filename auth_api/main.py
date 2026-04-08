from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from jose import jwt
from datetime import datetime, timedelta

app = FastAPI()

SECRET_KEY = "SHADOW_SECRET"
ALGORITHM = "HS256"

USER_DB = {"username": "admin", "password": "12345"}

@app.get("/", response_class=HTMLResponse)
async def login_page():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
        <style>
            body { background: #e9ecef; display: flex; align-items: center; height: 100vh; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            .card { border-radius: 15px; border: none; }
            .login-icon { font-size: 80px; color: #0d6efd; margin-bottom: 20px; }
            .text-center { text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-4">
                    <div class="card shadow-lg p-4 text-center">
                        <h3 class="mb-2">Login</h3>
                        <div class="login-icon">
                            <i class="fas fa-user-circle"></i>
                        </div>

                        <form id="loginForm" class="text-start">
                            <div class="mb-3">
                                <label class="form-label">Usuario</label>
                                <div class="input-group">
                                    <span class="input-group-text"><i class="fas fa-user"></i></span>
                                    <input type="text" id="username" name="username" class="form-control" required>
                                </div>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Contraseña</label>
                                <div class="input-group">
                                    <span class="input-group-text"><i class="fas fa-lock"></i></span>
                                    <input type="password" id="password" name="password" class="form-control" required>
                                </div>
                            </div>
                            <button type="submit" class="btn btn-primary w-100 shadow-sm mt-2">
                                <i class="fas fa-sign-in-alt me-2"></i>Ingresar
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>

        <script>
            document.getElementById('loginForm').addEventListener('submit', async (e) => {
                e.preventDefault();

                const formData = new FormData();
                formData.append('username', document.getElementById('username').value);
                formData.append('password', document.getElementById('password').value);

                try {
                    const response = await fetch('/auth', {
                        method: 'POST',
                        body: formData,
                        // Evitamos que el navegador intente seguir redirecciones automáticamente
                        redirect: 'manual' 
                    });

                    if (response.ok) {
                        const data = await response.json();
                        // Aquí es donde ocurre la magia: JS redirige manualmente
                        window.location.href = data.redirect_url;
                    } else {
                        Swal.fire({
                            title: 'Acceso Denegado',
                            text: 'Usuario o contraseña incorrectos. Por favor, intente nuevamente.',
                            icon: 'error',
                            confirmButtonColor: '#0d6efd',
                            confirmButtonText: 'Entendido'
                        });
                    }
                } catch (error) {
                    console.error(error);
                    Swal.fire({
                        title: 'Error de Conexión',
                        text: 'No se pudo conectar con el servidor de autenticación.',
                        icon: 'error'
                    });
                }
            });
        </script>
    </body>
    </html>
    """

@app.post("/auth")
async def auth(username: str = Form(...), password: str = Form(...)):
    if username == USER_DB["username"] and password == USER_DB["password"]:
        token = jwt.encode({"sub": username, "exp": datetime.utcnow() + timedelta(hours=1)}, SECRET_KEY, algorithm=ALGORITHM)
        
        # CAMBIO CLAVE: Devolvemos un JSON con la URL en lugar de redireccionar nosotros
        url = f"http://127.0.0.1:8000/dashboard/?auth_token={token}"
        return JSONResponse(content={"redirect_url": url})
    
    # Si falla, lanzamos el 401 que capturamos en el 'else' del JS
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")