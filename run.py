#!/usr/bin/env python3
"""
Script de inicio rápido para WebSocket REDUP.
Uso: python run.py [options]

Options:
  --dev              Modo desarrollo (default)
  --prod             Modo producción
  --check            Solo validar sin ejecutar
  --help             Mostrar ayuda
"""

import sys
import os
import argparse
from pathlib import Path


def validate():
    """Ejecutar validaciones previas"""
    print("🔍 Validando configuración...")
    
    # Verificar .env
    if not Path(".env").exists():
        print("⚠ .env no encontrado, usando valores por defecto")
    
    # Verificar imports
    required_packages = ["flask", "flask_socketio", "pymysql", "dotenv"]
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"✗ Faltan paquetes: {', '.join(missing)}")
        print("  Instala: pip install -r requirements.txt")
        return False
    
    print("✓ Todas las dependencias están instaladas")
    
    # Verificar BD (sin fallar)
    try:
        import pymysql
        from config import load_settings
        
        settings = load_settings()
        conn = pymysql.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            charset='utf8mb4',
            connect_timeout=5
        )
        conn.close()
        print(f"✓ BD conectada: {settings.db_name}@{settings.db_host}")
    except Exception as e:
        print(f"⚠ BD no disponible: {e}")
        print("  Asegúrate de que MySQL está ejecutándose")
        return False
    
    return True


def run_dev():
    """Ejecutar en modo desarrollo"""
    print("\n" + "="*60)
    print("🚀 Iniciando WebSocket REDUP (Desarrollo)")
    print("="*60)
    print("Logs detallados activados")
    print("Recarga automática al cambiar archivos activada")
    print("\nPara conectar desde Android:")
    print("  1. Obtén la IP de esta máquina:")
    print("     Windows: ipconfig | findstr IPv4")
    print("     Linux:   hostname -I")
    print("  2. En RED-UP Android, configura: http://<IP>:5000")
    print("\n" + "="*60 + "\n")
    
    os.environ["FLASK_ENV"] = "development"
    
    from app import app, socketio
    
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=False,  # Por si hay issues con reloader
        log_output=True
    )


def run_prod():
    """Ejecutar en modo producción"""
    print("\n" + "="*60)
    print("🚀 Iniciando WebSocket REDUP (Producción)")
    print("="*60)
    print("Modo de producción activado")
    print("Logs limitados (solo errores)")
    print("\n" + "="*60 + "\n")
    
    os.environ["FLASK_ENV"] = "production"
    
    from app import app, socketio
    
    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=False,
        log_output=False
    )


def main():
    parser = argparse.ArgumentParser(
        description="Iniciador de WebSocket REDUP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python run.py                    # Modo desarrollo (default)
  python run.py --prod            # Modo producción
  python run.py --check           # Solo validar
  python run.py --help            # Esta ayuda
        """
    )
    
    parser.add_argument(
        "--dev",
        action="store_true",
        default=True,
        help="Modo desarrollo (default)"
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Modo producción"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Solo validar sin ejecutar"
    )
    
    args = parser.parse_args()
    
    # Validar
    if not validate():
        sys.exit(1)
    
    if args.check:
        print("\n✓ Validación exitosa")
        print("  Ejecuta: python run.py")
        sys.exit(0)
    
    # Ejecutar
    try:
        if args.prod:
            run_prod()
        else:
            run_dev()
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor detenido")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
