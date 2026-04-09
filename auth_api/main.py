from fastapi import FastAPI, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext

# --- CONFIGURACIÓN DE BASE DE DATOS ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./usuarios.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo de Usuario
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

# Crear las tablas
Base.metadata.create_all(bind=engine)

# --- SEGURIDAD ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "SHADOW_SECRET"
ALGORITHM = "HS256"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- APP FASTAPI ---
app = FastAPI()

# Función para crear el usuario admin por defecto si no existe
def create_admin_user():
    db = SessionLocal()
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        hashed_pw = pwd_context.hash("12345")
        db.add(User(username="admin", hashed_password=hashed_pw))
        db.commit()
    db.close()

create_admin_user()

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
                        <div class="login-icon"><i class="fas fa-user-circle"></i></div>
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
    // Detectar si el token expiró al cargar la página
    window.addEventListener('DOMContentLoaded', () => {
        const urlParams = new URLSearchParams(window.location.search);
        
        if (urlParams.get('expired') === '1') {
            Swal.fire({
                title: 'Sesión Expirada',
                text: 'Tu token de seguridad ha caducado. Por favor, inicia sesión de nuevo.',
                icon: 'warning',
                confirmButtonColor: '#0d6efd',
                confirmButtonText: 'Entendido'
            });
            
            // Esto limpia la URL (?expired=1) para que si el usuario refresca 
            // el login manualmente, la alerta no vuelva a aparecer.
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    });

    // Tu lógica de autenticación (se queda igual)
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData();
        formData.append('username', document.getElementById('username').value);
        formData.append('password', document.getElementById('password').value);
        try {
            const response = await fetch('/auth', { method: 'POST', body: formData });
            if (response.ok) {
                const data = await response.json();
                window.location.href = data.redirect_url;
            } else {
                Swal.fire({ title: 'Acceso Denegado', text: 'Usuario o contraseña incorrectos.', icon: 'error' });
            }
        } catch (error) {
            Swal.fire({ title: 'Error', text: 'No hay conexión con la API.', icon: 'error' });
        }
    });
</script>
    </body>
    </html>
    """

@app.post("/auth")
async def auth(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # Buscamos al usuario en la base de datos
    user = db.query(User).filter(User.username == username).first()
    
    # Verificamos si existe y si la contraseña coincide (usando el verificador de hash)
    if user and pwd_context.verify(password, user.hashed_password):
        token = jwt.encode({"sub": username, "exp": datetime.utcnow() + timedelta(hours=1)}, SECRET_KEY, algorithm=ALGORITHM)
        url = f"http://127.0.0.1:8000/dashboard/?auth_token={token}"
        return JSONResponse(content={"redirect_url": url})
    
    raise HTTPException(status_code=401, detail="Credenciales incorrectas")

# --- NUEVO ENDPOINT PARA AÑADIR USUARIOS ---
@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El usuario ya existe")
    
    hashed_pw = pwd_context.hash(password)
    new_user = User(username=username, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    return {"message": f"Usuario {username} creado con éxito"}