DOMAIN = "judo_zewa_isafe"
PLATFORMS = ["sensor", "binary_sensor", "switch", "button", "number", "select"]
DEFAULT_PORT = 80
CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_HTTPS = "https"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SEND_DATA_AS_QUERY = "send_data_as_query"
DEFAULT_HTTPS = False
DEFAULT_VERIFY_SSL = True
DEFAULT_SEND_DATA_AS_QUERY = False  # POST first; switch if device needs GET

DEVICE_TYPE_ZEWA = 0x44  # per API docs

# API commands (hex function codes)
CMD_DEVICE_TYPE = "FF00"
CMD_SERIAL = "0600"
CMD_FW = "0100"
CMD_INSTALL_TS = "0E00"
CMD_TOTAL_WATER = "2800"  # liters, LSB first (4 bytes)

# ZEWA specific
CMD_ALARM_RESET = "6300"
CMD_CLOSE = "5100"
CMD_OPEN = "5200"
CMD_SLEEP_START = "5400"
CMD_SLEEP_STOP = "5500"
CMD_VAC_START = "5700"
CMD_VAC_STOP = "5800"
CMD_MICROLEAK_TEST = "5C00"
CMD_LEARN_START = "5D00"
CMD_ABSENCE_LIMITS_READ = "5E00"  # 3 x 2bytes: flow l/h, volume l, duration min
CMD_LEAK_SETTINGS_WRITE = "50"      # + 7 bytes payload
CMD_SLEEP_DURATION_WRITE = "53"     # + 1 byte (1..10 h)
CMD_SLEEP_DURATION_READ = "6600"    # -> 1 byte
CMD_VACATION_TYPE_WRITE = "56"      # + 1 byte (0..3)
CMD_LEARN_STATUS_READ = "6400"      # -> 1 byte active (0/1) + 2 bytes remaining liters
CMD_MICROLEAK_MODE_READ = "6500"    # -> 0 none,1 notify,2 notify+close
CMD_DATETIME_READ = "5900"          # -> 6 bytes (DD MM YY HH mm SS)
CMD_DATETIME_WRITE = "5A"           # + 6 bytes

# Statistics (optional services)
CMD_DAY = "FB"
CMD_WEEK = "FC"
CMD_MONTH = "FD"
CMD_YEAR = "FE"