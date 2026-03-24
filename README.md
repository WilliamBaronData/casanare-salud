# Casanare Smart Health — Plataforma de Vigilancia Epidemiológica

Dashboard interactivo para exposiciones mensuales de la Secretaría de Salud de Casanare.

---

## Uso mensual (reutilización)

Cada mes, solo necesitas:

1. Descargar el nuevo archivo IEC del sistema de campo
2. Abrir el link del dashboard en el navegador
3. En el panel lateral → **"Cargar archivo IEC"** → seleccionar el nuevo archivo
4. Los filtros, gráficas y mapa se actualizan automáticamente

**No se requiere tocar código.** El sistema detecta automáticamente los municipios, eventos y semanas del nuevo archivo.

---

## Archivos compatibles

| Formato | Compatibilidad |
|---------|----------------|
| `.xls`  | ✅ Convierte automáticamente |
| `.xlsx` | ✅ Carga directa |

El sistema espera el formulario IEC con las columnas estándar del SIVIGILA Colombia.

---

## Despliegue en la nube (Streamlit Community Cloud)

### Primer despliegue

1. Crear repositorio en GitHub llamado `casanare-smart-health`
2. Subir los archivos:
   - `app.py`
   - `requirements.txt`
3. Ir a [share.streamlit.io](https://share.streamlit.io)
4. **New app** → seleccionar el repositorio → archivo `app.py`
5. **Deploy** — en 2-3 minutos tendrás tu URL

La URL quedará fija para siempre, por ejemplo:
```
https://casanare-smart-health.streamlit.app
```

### Actualizaciones de código

Si en el futuro necesitas actualizar el código, simplemente sube el nuevo `app.py` al repositorio de GitHub. Streamlit Cloud se actualiza automáticamente en segundos.

---

## Ajuste si cambia el formulario IEC

Si en el futuro el formulario tiene columnas con nombres diferentes, edita **solo esta sección** al inicio de `app.py`:

```python
COLS = {
    'evento':      '13_Evento_objeto_de_',   # ← cambiar aquí
    'municipio':   '3_Municipio',
    'semana':      '14_Semana_epidemiolg',
    ...
}
```

El resto del código se adapta automáticamente.

---

## Funcionalidades

- **Mapa georreferenciado** con datos GPS reales del formulario IEC
- **Curva epidémica semanal** por tipo de evento (sin signos, con signos, grave, mortalidad)
- **Distribución por municipio** con escala de colores por intensidad
- **Pirámide de edad** por grupos etarios
- **Distribución por sexo** con gráfica de dona
- **Nivel de alerta dinámico** calculado automáticamente (normal / monitoreo / alerta alta / crítica)
- **Filtros combinables**: evento, municipio, semana, área
- **Tabla de detalle** exportable con hasta 500 registros

---

## Estructura del proyecto

```
casanare-smart-health/
├── app.py              ← Código principal (único archivo a mantener)
└── requirements.txt    ← Dependencias (no modificar)
```
