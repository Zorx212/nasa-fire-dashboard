## Tabla maestra v0 (6 PSI, 1007 filas)
- Conversiones: PSI-159 XO2 x100 -> o2_percent, approx p (bar) x100 -> pressure_kpa; PSI-39 Oxygen x100 -> o2_percent, "1 atm" -> 101.325 kPa; PSI-99 "~ 22.1" -> 22.1 (%)
- Flujo en cm/s en PSI-99, 101, 102 y 107, sin conversión
- PSI-39: 8 filas duplicadas idénticas eliminadas (87 -> 79)
- PSI-107: varias filas por ignición (mismo día y hora, distinto flujo), inferido de los datos; el prefijo del ID las agrupa. Reportes (30 day y Final) aún sin revisar.
- PSI-101: ID = test + material, porque el test 57 aparece con lampwick y teflon
- flame_spread_rate: solo tiene valor en PSI-99-2-5 y PSI-99-2-6; las demás tablas no lo miden
- PSI-22 fuera: la tabla es por día de pruebas, no por ensayo
- Por confirmar en reportes: SE y FT (PSI-159), material_type líquido de PSI-39, dibutil ftalato (PSI-102) como líquido, valores negativos de aire en PSI-107
- doi, license y title salen de data/catalog.csv.

## PSI-99 (propagación en sólidos)
- 9 ensayos (2-1 a 2-9): silicona, SIBAL, PMMA, Nomex. O2 21.5–22.1 %, flujo 20 cm/s. Sin presión en la tabla.
- Se ingieren solo las columnas de microgravedad (?-g). Las de 1-g (gravedad terrestre) quedan en notes con su etiqueta, porque no son microgravedad.
- flame_spread_rate: 2.1 mm/s (2-5) y 2.6 mm/s (2-6). Los demás ensayos no tienen velocidad.
- flame_outcome: se extinguió en 2-1 a 2-4 (quemado ~0); propagó en 2-5 y 2-6 (hay velocidad); vacío en 2-7 (PMMA y Nomex mezclados), 2-8 y 2-9 (llama anclada, regresión de 0.01 a 0.04 mm/s, que no es propagación).
- PSI-99, 2-1 a 2-4: la fuente indica que no hubo propagación (?-g Burn Length "~ 0", Burn Time "Insignificant"). El vocabulario del contrato solo tiene "propagó" y "se extinguió", así que se marcaron "se extinguió".
- O2 "22.1 to 22.0" se toma al inicio (22.1). Según Note 1, el O2 se deriva de la producción de CO2.
- Material de 2-6 y 2-9 estaba vacío (celdas combinadas): se tomó el de la fila anterior (SIBAL y PMMA). SUPUESTO.
- Notas al pie del CSV original: Nota 2: la parte de PMMA se consumió por completo y el Nomex no se encendió. Nota 3: es la longitud de combustible con daño visible significativo. Nota 4: la llama queda anclada en la base de la muestra, con regresión muy lenta (0.01 a 0.04 mm/s).
- Por confirmar en el reporte (SAFFIRE-II DoD): que "?-g" sea microgravedad, que "?-g Spread Length" sea velocidad (los valores están en mm/s), la presión de la cámara, el material de 2-6 y 2-9, y el flujo (20 cm/s en el CSV contra 30 cm/s).

## Correcciones del PR #10
- gravity_level = 0 (en g) en todas las filas: todos los experimentos son en microgravedad. Es un valor real, no un faltante.
- material_type en español: gas (PSI-107, 159), sólido (PSI-99, 101, 102), líquido (PSI-39 y dibutil ftalato de PSI-102).
- flame_outcome: SE = "se extinguió" (183 filas de PSI-159; las otras 4 de las 187 son PSI-99, 2-1 a 2-4, por otra regla). FT = "flow terminated" (lectura por el nombre de la columna, sin confirmar). Va vacío porque describe cómo terminó la prueba, no lo que hizo la llama; el código original queda en notes. Pendiente de confirmar en el reporte de PSI-159.
- SE y FT (PSI-159): INTERPRETACIÓN SIN CONFIRMAR. SE = self-extinguished; FT = flow terminated.
- material_type líquido (PSI-39): INTERPRETACIÓN SIN CONFIRMAR, deducida del combustible (C12H26 / iso-dodecano). Pendiente de confirmar en el reporte.
- flow_velocity negativo en PSI-107 (8 filas): pendiente de confirmar en el reporte (convención de signo o error). Los valores se conservan tal cual y las 8 filas llevan en notes "flow_velocity negativo sin confirmar".
- spread_rate_unit solo tiene valor (mm/s) donde hay flame_spread_rate (2 filas: PSI-99-2-5 y 2-6) y queda vacía en el resto. La regla está en src/normalize.py.