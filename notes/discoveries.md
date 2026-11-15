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