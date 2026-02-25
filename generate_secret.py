#!/usr/bin/env python3
"""
Script para generar SECRET_KEY segura y verificar configuración.
"""
import secrets
import os

def generate_secret_key():
    """Genera una SECRET_KEY aleatoria segura."""
    return secrets.token_urlsafe(32)

def check_env_file():
    """Verifica si existe archivo .env y su configuración."""
    if not os.path.exists('.env'):
        print("⚠️  Archivo .env NO encontrado")
        print("   Copia .env.example a .env:")
        print("   copy .env.example .env  (Windows)")
        print("   cp .env.example .env    (Linux/Mac)")
        return False
    
    print("✅ Archivo .env encontrado")
    
    # Leer y verificar SECRET_KEY
    with open('.env', 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'super-secret-key-change-me-in-production' in content:
        print("⚠️  Usando SECRET_KEY por defecto (NO segura)")
        print("   Genera una nueva con este script")
    elif 'SECRET_KEY=' in content:
        print("✅ SECRET_KEY configurada")
    
    if 'FLASK_ENV=production' in content:
        print("✅ Modo: PRODUCCIÓN")
        if 'CORS_ALLOWED_ORIGINS=*' in content:
            print("⚠️  CORS abierto (*) en producción - NO recomendado")
        else:
            print("✅ CORS configurado con dominios específicos")
    else:
        print("ℹ️  Modo: DESARROLLO")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("🔐 Generador de SECRET_KEY para Flask-SocketIO")
    print("=" * 60)
    print()
    
    # Generar nueva clave
    new_key = generate_secret_key()
    print(f"Nueva SECRET_KEY generada:")
    print(f"  {new_key}")
    print()
    print("Cópiala a tu archivo .env:")
    print(f"  SECRET_KEY={new_key}")
    print()
    
    # Verificar configuración actual
    print("-" * 60)
    print("Verificación de configuración:")
    print()
    check_env_file()
    print()
    print("=" * 60)
