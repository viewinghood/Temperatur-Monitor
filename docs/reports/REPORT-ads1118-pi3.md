# ADS1118 TempMonitor — Hardware & Treiber-Report

**Datum:** 2026-07-04  
**Basis:** `spi_adc_tm_try2.py`, [viewinghood/ads1118](https://github.com/viewinghood/ads1118) (MicroPython)  
**Ziel:** Python3-Treiber für Raspberry Pi 3 + Testprogramm `spi_adc_tm_try3.py`

---

## 1. Hardware-Übersicht (aus `spi_adc_tm_try2.py`)

| Komponente | Wert |
|------------|------|
| Host | Raspberry Pi 3 (`raspi3`), Python 3.5.3 |
| ADC-Chips | 2× Texas Instruments ADS1118 (U1, U2) |
| Interface | SPI0, **Mode 1** (CPOL=0, CPHA=1) |
| SPI-Takt | 50 kHz (`max_speed_hz=50000`) |
| Übertragung | 32 Bit pro Transfer — 16-Bit-Konfigurationswort **zweimal** hintereinander |

### SPI-Chip-Select (spidev)

| PCB | spidev | BOARD-Pin | BCM-GPIO | Hinweis |
|-----|--------|-----------|----------|---------|
| **U1** | `open(0, 0)` CS0 | Pin 24 | GPIO8 | `ads1118_u1` in try2 |
| **U2** | `open(0, 1)` CS1 | Pin 26 | GPIO7 | `ads1118_u2` in try2 |

Quelle GPIO: `gpio_cs_test_tm.py` — CS0=GPIO8, CS1=GPIO7.

### Thermoelemente (Typ K, differentielle Eingänge)

| Sensor | ADC | MUX | Eingänge | Status (Stand Test) |
|--------|-----|-----|----------|---------------------|
| **TC1** | U1 | AIN0−AIN1 | Diff Kanal 0 | **angeschlossen** (Typ K) |
| **TC2** | U1 | AIN2−AIN3 | Diff Kanal 1 | nicht angeschlossen |
| **TC3** | U2 | AIN0−AIN1 | Diff Kanal 0 | nicht angeschlossen |
| **TC4** | U2 | AIN2−AIN3 | Diff Kanal 1 | nicht angeschlossen |

### Analog-Frontend (aus MicroPython-Treiber)

- Isolations-/Verstärker-Stufe mit **Gain ≈ 16.2×** vor dem ADS1118 (Kommentar im Original-Treiber)
- Standard-PGA für Diff-Kanäle: **±2.048 V** (`PGA_2_048V`)

---

## 2. Konfigurationsregister (try2, Chip-Temperatur)

try2 sendet für interne Temperaturmessung:

```
MSB = 0x8F = 0b10001111
LSB = 0x1B = 0b00011011
→ 16-Bit-Wort: 0x8F1B
```

| Feld | Bits | Wert | Bedeutung |
|------|------|------|-----------|
| SS | 15 | 1 | Single-shot start |
| MUX | 14–12 | 000 | AIN0−AIN1 (irrelevant in TS-Mode) |
| PGA | 11–9 | 111 | ±0.256 V |
| MODE | 8 | 0 | Continuous |
| DR | 7–5 | 011 | 64 SPS |
| **TS_MODE** | **4** | **1** | **Interner Temperatursensor** |
| PULL_UP | 3 | 1 | DOUT Pull-up aktiv |
| NOP | 2–1 | 01 | Valid data |
| Res | 0 | 1 | Reserved (always 1) |

Für ADC-Spannungsmessung (auskommentiert in try2): LSB = **0x0B** (TS_MODE=0).

### Temperatur-Dekodierung (try2)

```
14-Bit linksbündig: 00 S MMMMMM MMLLLLLL LL
raw = (dataMSB << 6) + (dataLSB >> 2)   [signed wenn MSB bit7 gesetzt]
T_chip = raw × 0.03125 °C
```

Beispiel aus Messung: raw=939 → 939 × 0.03125 = **29.344 °C** (U1).

---

## 3. Bekannter Fehler in try2 — vertauschte U1/U2-Labels

```python
devices = [ads1118_u2, ads1118_u1]   # ← vertauscht!
for channel, spi_dev in enumerate(devices):
    print("ADC U{}".format(channel+1))
```

| Loop `channel` | Druck | Tatsächlicher Chip |
|----------------|-------|-------------------|
| 0 | „U1“ | **U2** (CS1) |
| 1 | „U2“ | **U1** (CS0) |

**try3 korrigiert das:** U1 = CS0, U2 = CS1.

---

## 4. MicroPython-Treiber → Python3 Portierung

Quelle: [ads1118.py auf GitHub](https://github.com/viewinghood/ads1118/blob/main/ads1118.py)

| MicroPython | Python3 / Raspberry Pi |
|-------------|------------------------|
| `machine.SPI` + `machine.Pin(NSS)` | `spidev.SpiDev` (CS durch `open(bus, cs)`) |
| `spi.write_readinto(tx, rx)` 16 Bit | `spi.xfer2([msb,lsb,msb,lsb])` 32 Bit (wie try2) |
| `time.sleep_ms(n)` | `time.sleep(n/1000.0)` |
| `Pin(nss, OUT)` manuelles CS | nicht nötig — spidev toggelt CS |

Beibehalten aus Original:

- `_encodeCommand()` — 16-Bit-Konfigurationswort
- MUX-/PGA-/DR-Konstanten
- `ADC_CONVERSION_FACTORS`, Kaltstellen-Kompensation für Typ K
- Mehrfach-MUX-Array pro Chip (`[AIN0−AIN1, AIN2−AIN3]`)

---

## 5. Typ-K Thermoelement — Berechnung

1. **Kaltstelle:** interner Chip-Temperatursensor (`T_cj`)
2. **Spannung:** differentieller ADC-Kanal → `V_adc` (mit PGA 2.048 V)
3. **Entstörung Gain:** `V_tc = V_adc / 16.2`
4. **Seebeck-Spannung → Delta-T:** NIST-Näherung (0–500 °C): `ΔT ≈ V_tc_µV / 40.6`
5. **Prozess-Temperatur:** `T_hot = T_cj + ΔT`

---

## 6. Erkennung nicht angeschlossener Sensoren (Heuristik)

Mehrfach-Sampling (5×) pro Kanal:

| Kriterium | Interpretation |
|-----------|----------------|
| \|raw\| > 30 000 | Saturation / offener Eingang |
| \|mean V\| > 10 mV | **Nicht verbunden** — schwebender Bias (~±320 mV beobachtet) |
| \|raw\| ≤ 200, kleine Spannung | Thermoelement verbunden (CJC-Gleichgewicht) |

**Messung try3 (2026-07-04):** TC1 raw≈3, ~0.2 mV → verbunden. TC2/TC3 ~+320 mV, TC4 ~−170 mV → offen.

---

## 7. Dateien in diesem Schritt

| Datei | Rolle |
|-------|-------|
| `ads1118.py` | Python3-Treiber (spidev) |
| `spi_adc_tm_try3.py` | Test: Chip-Temp U1/U2 + TC1–TC4 |
| `REPORT-ads1118-pi3.md` | Dieser Report |

---

## 8. Ergebnis `spi_adc_tm_try3.py` (Pi-Lauf 2026-07-04)

### Chip-Temperaturen (interner Sensor)

| Chip | Zyklus 1 | Zyklus 2 | try2-Vergleich |
|------|----------|----------|----------------|
| U1 (CS0) | 33.47 °C | 33.47 °C | ~30 °C (try2 Label vertauscht) |
| U2 (CS1) | 34.38 °C | 34.34 °C | ~29 °C |

Die absoluten Werte sind höher als in try2 (~29–30 °C) — vermutlich realere Umgebungstemperatur am Messzeitpunkt; der Treiber liefert konsistente, stabile Werte.

### Thermoelemente

| Sensor | Status | ADC mean | raw | Bewertung |
|--------|--------|----------|-----|-----------|
| **TC1** U1 AIN0−AIN1 | **connected** | ~0.20 mV | 3 | Typ K ≈ 33.47 °C (= Kaltstelle, kein ΔT) ✓ |
| **TC2** U1 AIN2−AIN3 | **not connected** | +320.5 mV | ~5127 | Floating-Bias ✓ |
| **TC3** U2 AIN0−AIN1 | **not connected** | +319.3 mV | ~5108 | Floating-Bias ✓ |
| **TC4** U2 AIN2−AIN3 | **not connected** | −170…−182 mV | ~−2726…−2911 | Floating-Bias (negativ) ✓ |

**Alle vier Kanäle korrekt erkannt** — TC1 verbunden, TC2–TC4 offen.

### Fazit

- Python3-Treiber `ads1118.py` funktioniert auf dem Pi (Python 3.5.3).
- Chip-Temperatur identisch zur try2-Methode (0x8F/0x1B, 32-Bit-SPI).
- Typ-K-Anzeige für TC1 sinnvoll: Thermoelement bei Raumtemperatur → Prozess-T ≈ Kaltstell-T.
- Nächster Schritt: TC1 mit Wärmequelle testen (ΔT > 0 sichtbar).

---

*Autor Analyse: Cursor Agent — Basis-Treiber © Richard Heming (MIT)*
