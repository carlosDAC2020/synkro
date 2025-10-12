# -*- coding: utf-8 -*-
"""
Script para actualizar el plan_cargue de las rutas existentes
agregando información de contacto de los clientes
"""
import os
import sys
import django

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import RutaEntrega, Venta

def actualizar_rutas():
    rutas = RutaEntrega.objects.all()
    rutas_actualizadas = 0
    
    print(f"📦 Encontradas {rutas.count()} rutas para actualizar...")
    print("=" * 60)
    
    for ruta in rutas:
        print(f"\n🔄 Actualizando Ruta #{ruta.id}...")
        
        # Obtener el plan de cargue actual
        plan_cargue = ruta.plan_cargue
        
        if not plan_cargue:
            print(f"  ⚠️  Ruta #{ruta.id} no tiene plan de cargue, saltando...")
            continue
        
        # Actualizar cada item del plan de cargue
        plan_actualizado = False
        for item in plan_cargue:
            # Si ya tiene los campos de contacto, saltar
            if 'telefono' in item and 'email' in item:
                continue
            
            # Buscar la venta correspondiente
            try:
                venta = Venta.objects.get(id=item['venta_id'])
                
                # Agregar información de contacto
                if venta.cliente:
                    item['telefono'] = venta.cliente.telefono if venta.cliente.telefono else 'N/A'
                    item['email'] = venta.cliente.email if venta.cliente.email else 'N/A'
                else:
                    item['telefono'] = 'N/A'
                    item['email'] = 'N/A'
                
                plan_actualizado = True
                print(f"  ✅ Item actualizado: {item['cliente']} - Tel: {item['telefono']}")
                
            except Venta.DoesNotExist:
                print(f"  ⚠️  Venta #{item['venta_id']} no encontrada")
                item['telefono'] = 'N/A'
                item['email'] = 'N/A'
        
        # Guardar la ruta actualizada
        if plan_actualizado:
            ruta.plan_cargue = plan_cargue
            ruta.save()
            rutas_actualizadas += 1
            print(f"  💾 Ruta #{ruta.id} guardada con éxito")
        else:
            print(f"  ℹ️  Ruta #{ruta.id} ya tenía la información de contacto")
    
    print("\n" + "=" * 60)
    print(f"✅ Proceso completado!")
    print(f"📊 Rutas actualizadas: {rutas_actualizadas} de {rutas.count()}")

if __name__ == '__main__':
    print("🚀 Iniciando actualización de rutas...")
    print("=" * 60)
    actualizar_rutas()
    print("\n✨ ¡Listo! Ahora puedes descargar los PDFs con la información de contacto.")
