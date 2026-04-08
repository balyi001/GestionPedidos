from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
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
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background: #e9ecef; display: flex; align-items: center; height: 100vh; }
            .card { border-radius: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-4">
                    <div class="card shadow-lg p-4">
                        <h3 class="text-center mb-4">Login Sistema</h3>
                        <form action="/auth" method="post">
                            <div class="mb-3">
                                <label>Usuario</label>
                                <input type="text" name="username" class="form-control" required>
                            </div>
                            <div class="mb-3">
                                <label>Contraseña</label>
                                <input type="password" name="password" class="form-control" required>
                            </div>
                            <button type="submit" class="btn btn-primary w-100">Ingresar</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.post("/auth")
async def auth(username: str = Form(...), password: str = Form(...)):
    if username == USER_DB["username"] and password == USER_DB["password"]:
        token = jwt.encode({"sub": username, "exp": datetime.utcnow() + timedelta(hours=1)}, SECRET_KEY, algorithm=ALGORITHM)
        # Redirige a Django pasando el token por URL (para validación posterior)
        return RedirectResponse(url=f"http://127.0.0.1:8000/pedidos/?auth_token={token}", status_code=302)
    return HTMLResponse("<h2>Error: Usuario incorrecto</h2><a href='/'>Volver</a>", status_code=401)