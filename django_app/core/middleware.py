from django.shortcuts import redirect
from django.conf import settings
from jose import jwt, JWTError

class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Intentar capturar el token si viene en la URL (primer login)
        token_url = request.GET.get('auth_token')
        if token_url:
            request.session['auth_token'] = token_url
            # Limpiamos la URL para que no se vea el token
            return redirect(request.path)

        # 2. Obtener el token de la sesión de Django
        token = request.session.get('auth_token')

        token_url = request.GET.get('auth_token')
        if token_url:
            request.session['auth_token'] = token_url
            return redirect(request.path)

        token = request.session.get('auth_token')

        # 3. Verificar si el token es válido
        if not token:
            return redirect(settings.LOGIN_URL_EXTERNAL)

        try:
            # Intentamos decodificarlo. Si expiró o es falso, saltará al except
            jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        except JWTError:
            # Si el token no sirve, borramos la sesión y mandamos al login
            if 'auth_token' in request.session:
                del request.session['auth_token']
            return redirect(f"{settings.LOGIN_URL_EXTERNAL}?expired=1")

        return self.get_response(request)