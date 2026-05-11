"""Konstanten für die JUDO ZEWA i-SAFE Integration."""

DOMAIN = "judo_leakguard"

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "Connectivity"
DEFAULT_SCAN_INTERVAL = 30  # Sekunden

# Gerätetyp-ID für ZEWA i-SAFE
DEVICE_TYPE_ZEWA_ISAFE = 0x44

# ── API-Kommandos ─────────────────────────────────────────────────────────────

# Geräteinfos (read-only)
CMD_DEVICE_TYPE = "FF00"          # 1 B Gerätetyp
CMD_SERIAL_NUMBER = "0600"        # 4 B Seriennummer (LSB-first)
CMD_FW_VERSION = "0100"           # 3 B Firmware-Version
CMD_COMMISSION_DATE = "0E00"      # 4 B Unix-Timestamp (BE)
CMD_TOTAL_WATER = "2800"          # 4 B Gesamtwasser in Litern (LSB-first)

# Datum/Zeit
CMD_READ_DATETIME = "5900"        # 6 B: Tag, Monat, Jahr, Stunde, Min, Sek
CMD_WRITE_DATETIME = "5A"         # + 6 B wie oben

# Ventil
CMD_VALVE_CLOSE = "5100"          # Leckageschutz schließen
CMD_VALVE_OPEN = "5200"           # Leckageschutz öffnen

# Sleep-Modus
CMD_SLEEP_START = "5400"          # Sleepmodus starten
CMD_SLEEP_STOP = "5500"           # Sleepmodus beenden
CMD_SET_SLEEP_HOURS = "53"        # + 1 B (1..10 h)
CMD_READ_SLEEP_HOURS = "6600"     # 1 B (1..10 h)

# Urlaubsmodus
CMD_VACATION_START = "5700"       # Urlaubsmodus starten
CMD_VACATION_STOP = "5800"        # Urlaubsmodus beenden
CMD_SET_VACATION_TYPE = "56"      # + 1 B (0=aus, 1=U1, 2=U2, 3=U3)

# Lernmodus
CMD_LEARN_START = "5D00"          # Lernmodus starten
CMD_READ_LEARN_STATUS = "6400"    # 1 B aktiv + 2 B Rest-Liter

# Mikroleck-Test
CMD_MICROLEAK_TEST = "5C00"       # Einmaligen Test starten
CMD_READ_MICROLEAK_MODE = "6500"  # 1 B: 0=off, 1=notify, 2=notify+close
CMD_SET_MICROLEAK_MODE = "5B"     # + 1 B (0/1/2)

# Abwesenheitslimits
CMD_READ_ABSENCE_LIMITS = "5E00"  # 6 B: Flow (U16), Volume (U16), Time (U16) – LSB-first
CMD_WRITE_ABSENCE_LIMITS = "5F"   # + 6 B wie oben

# Leckage-Einstellungen (kombinierter Schreibbefehl)
CMD_WRITE_LEAK_PRESET = "50"      # + 7 B

# Meldungen zurücksetzen
CMD_ACK_ALARM = "6300"

# Abwesenheitszeitpläne (Index 0..6)
CMD_READ_ABSENCE_SCHEDULE = "60"  # + 1 B Index → 6 B zurück
CMD_WRITE_ABSENCE_SCHEDULE = "61" # + 7 B (Index + 6 B)
CMD_DELETE_ABSENCE_SCHEDULE = "62"# + 1 B Index

# Statistiken
CMD_STAT_DAY = "FB"               # + 4 B (Tag, Monat, Jahr 2B) → 32 B
CMD_STAT_WEEK = "FC"              # + 3 B (KW, Jahr 2B) → 28 B
CMD_STAT_MONTH = "FD"             # + 3 B (Monat, Jahr 2B) → 124 B
CMD_STAT_YEAR = "FE"              # + 2 B (Jahr 2B) → 48 B

# ── Wochentage (API: 0=So, 1=Mo, ..., 6=Sa) ──────────────────────────────────
WEEKDAYS = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"]

# ── Urlaubstypen ──────────────────────────────────────────────────────────────
VACATION_TYPES = {
    0: "off",
    1: "u1",
    2: "u2",
    3: "u3",
}
VACATION_TYPES_REVERSE = {v: k for k, v in VACATION_TYPES.items()}

# ── Mikroleck-Modi ────────────────────────────────────────────────────────────
MICROLEAK_MODES = {
    0: "off",
    1: "notify",
    2: "notify_and_close",
}
MICROLEAK_MODES_REVERSE = {v: k for k, v in MICROLEAK_MODES.items()}

# ── Plattformen ───────────────────────────────────────────────────────────────
PLATFORMS = [
    "sensor",
    "binary_sensor",
    "switch",
    "button",
    "number",
    "select",
]
