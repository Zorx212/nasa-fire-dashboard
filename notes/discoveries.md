## Tabla maestra v0 (5 PSI, 998 filas)
- Conversiones: PSI-159 XO2 x100 -> o2_percent, approx p (bar) x100 -> pressure_kpa; PSI-39 Oxygen x100 -> o2_percent, "1 atm" -> 101.325 kPa
- Flujo en cm/s en PSI-101, 102 y 107, sin conversión
- PSI-39: 8 filas duplicadas idénticas eliminadas (87 -> 79)
- PSI-107: varias filas por ignición (mismo día y hora, distinto flujo), inferido de los datos; el prefijo del ID las agrupa. Sin PDF revisado.
- PSI-101: ID = test + material, porque el test 57 aparece con lampwick y teflon
- flame_spread_rate vacío en todas las filas: ninguna tabla lo mide
- PSI-22 fuera: la tabla es por día de pruebas, no por ensayo
- Por confirmar en reportes: SE y FT (PSI-159), material_type liquid de PSI-39, Dibutyl Phthalate (PSI-102), valores negativos de aire en PSI-107
- Sin data/catalog.csv: doi, license y title vacíos
## PSI-99 (propagación en sólidos)
- 9 ensayos (2-1 a 2-9): silicona, SIBAL, PMMA, Nomex. O2 21.5–22.1 %, flujo 20 cm/s. Sin presión en la tabla.
- Se ingieren solo las columnas de microgravedad (?-g). Las de 1-g (gravedad terrestre) quedan en notes con su etiqueta, porque no son microgravedad.
- flame_spread_rate: 2.1 mm/s (2-5) y 2.6 mm/s (2-6). Los demás ensayos no tienen velocidad.
- flame_outcome: se extinguió en 2-1 a 2-4 (quemado ~0); propagó en 2-5 y 2-6 (hay velocidad); vacío en 2-7 (PMMA y Nomex mezclados), 2-8 y 2-9 (llama anclada, regresión de 0.01 a 0.04 mm/s, que no es propagación).
- O2 "22.1 to 22.0" se toma al inicio (22.1). Según Note 1, el O2 se deriva de la producción de CO2.
- Material de 2-6 y 2-9 estaba vacío (celdas combinadas): se tomó el de la fila anterior (SIBAL y PMMA). SUPUESTO.
- Notas al pie del CSV original: Nota 2: la parte de PMMA se consumió por completo y el Nomex no se encendió. Nota 3: es la longitud de combustible con daño visible significativo. Nota 4: la llama queda anclada en la base de la muestra, con regresión muy lenta (0.01 a 0.04 mm/s).
- Por confirmar en el reporte: que "?-g" sea microgravedad, que "?-g Spread Length" sea velocidad (los valores están en mm/s), la presión de la cámara y el material de 2-6 y 2-9.