#!/usr/bin/env python3
"""
Script para validar que WebSocket funciona de forma independiente (standalone).
Verifica:
- Configuración cargada correctamente desde .env
- No hay referencias hardcodeadas a API
- Módulos requeridos están disponibles
- Conexión a BD se intenta correctamente
"""

import sys
import os
from pathlib import Path

def check_imports():
    """Verificar que todos los imports necesarios funcionan"""
    print("✓ Verificando imports...")
    try:
        from dotenv import load_dotenv
        print("  ✓ python-dotenv")
        from flask import Flask
        print("  ✓ Flask")
        from flask_socketio import SocketIO
        print("  ✓ Flask-SocketIO")
        from flask_cors import CORS
        print("  ✓ Flask-CORS")
        import pymysql
        print("  ✓ PyMySQL")
        import cloudinary
        print("  ✓ Cloudinary")
        return True
    except ImportError as e:
        print(f"  ✗ Error de import: {e}")
        return False


def check_env_files():
    """Verificar que existen archivos .env necesarios"""
    print("\n✓ Verificando archivos .env...")
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print(f"  ✓ .env existe ({env_file.stat().st_size} bytes)")
    elif env_example.exists():
        print(f"  ⚠ .env NO existe, pero .env.example presente")
        print(f"    → Se usarán valores por defecto de config.py")
    else:
        print(f"  ⚠ No hay archivos .env ni .env.example")
    
    return True


def check_configuration():
    """Verificar que la configuración carga sin errores"""
    print("\n✓ Verificando configuración...")
    try:
        from config import load_settings
        settings = load_settings()
        
        print(f"  ✓ Secret Key: {'***' if settings.secret_key else 'NO CONFIGURADA'}")
        print(f"  ✓ Flask Environment: {settings.flask_env}")
        print(f"  ✓ Host: {settings.host}")
        print(f"  ✓ Port: {settings.port}")
        print(f"  ✓ CORS Origins: {settings.cors_allowed_origins}")
        print(f"  ✓ DB Host: {settings.db_host}")
        print(f"  ✓ DB Port: {settings.db_port}")
        print(f"  ✓ DB User: {settings.db_user}")
        print(f"  ✓ DB Name: {settings.db_name}")
        print(f"  ✓ Cloudinary Configured: {settings.cloudinary_configured}")
        
        return True, settings
    except Exception as e:
        print(f"  ✗ Error cargando configuración: {e}")
        return False, None


def check_no_api_references():
    """Verificar que no hay referencias hardcodeadas a API"""
    print("\n✓ Verificando ausencia de referencias a API...")
    
    api_patterns = [
        "localhost:8000",
        "127.0.0.1:8000",
        "API_UPRed",
        "http://api",
        "https://api",
        "fastapi"
    ]
    
    files_to_check = ["app.py", "config.py", "services/cloudinary_service.py"]
    issues = []
    
    for filename in files_to_check:
        if not os.path.exists(filename):
            continue
            
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            for pattern in api_patterns:
                if pattern.lower() in content:
                    issues.append(f"  ✗ {filename} contiene: {pattern}")
    
    if issues:
        for issue in issues:
            print(issue)
        return False
    else:
        print("  ✓ No hay referencias a API detectadas")
        return True


def check_db_connectivity(settings):
    """Intentar conexión a BD (sin fallar si no está disponible)"""
    print("\n✓ Verificando conectividad a BD...")
    try:
        import pymysql
        from contextlib import contextmanager
        
        @contextmanager
        def get_db_connection():
            conn = pymysql.connect(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name,
                charset='utf8mb4',
                connect_timeout=5
            )
            try:
                yield conn
            finally:
                conn.close()
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                print(f"  ✓ BD conectada: {settings.db_name}@{settings.db_host}")
                return True
        except pymysql.Error as e:
            print(f"  ⚠ BD no disponible: {e}")
            print(f"    → Asegúrate de que MySQL está ejecutándose")
            print(f"    → Host: {settings.db_host}:{settings.db_port}")
            print(f"    → User: {settings.db_user}")
            return False
    except ImportError:
        print(f"  ⚠ PyMySQL no instalado (se requiere para deploy)")
        return False
    except Exception as e:
        print(f"  ⚠ Error conectando a BD: {e}")
        return False


def check_file_provider_config():
    """Verificar que el FileProvider está configurado"""
    print("\n✓ Verificando configuración de archivos...")
    
    xml_path = "app/src/main/res/xml/file_paths.xml" if os.name == 'nt' else "file_paths.xml"
    
    if os.path.exists(xml_path):
        print(f"  ✓ file_paths.xml presente")
        return True
    else:
        print(f"  ⚠ file_paths.xml no encontrado (esperado en Android)")
        return True  # No es crítico para WebSocket


def main():
    print("=" * 70)
    print("VALIDACIÓN: WebSocket REDUP Standalone")
    print("=" * 70)
    
    all_good = True
    
    # Verificaciones
    if not check_imports():
        print("\n✗ Faltan dependencias. Instala: pip install -r requirements.txt")
        all_good = False
    
    if not check_env_files():
        all_good = False
    
    config_ok, settings = check_configuration()
    if not config_ok:
        all_good = False
    
    if not check_no_api_references():
        print("\n✗ Se encontraron referencias hardcodeadas a API")
        all_good = False
    else:
        print("\n✓ WebSocket es completamente independiente (standalone)")
    
    if settings and not check_db_connectivity(settings):
        print("\n⚠ Aviso: BD no disponible en este momento")
        print("  Esto es OK para desarrollo/testing, pero se requiere para deploy")
    
    check_file_provider_config()
    
    # Resultado final
    print("\n" + "=" * 70)
    if all_good:
        print("✓ VALIDACIÓN EXITOSA: WebSocket está listo para deploy")
        print("\nPara iniciar el servidor:")
        print("  python app.py")
        print("\nOpciones:")
        print("  - Development: FLASK_ENV=development python app.py")
        print("  - Production: FLASK_ENV=production python app.py")
        print("=" * 70)
        return 0
    else:
        print("✗ VALIDACIÓN CON PROBLEMAS: revisa los errores arriba")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
