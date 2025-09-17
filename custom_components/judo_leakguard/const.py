DOMAIN = "judo_leakguard"
DEFAULT_SCAN_INTERVAL = 30  # seconds
CONF_HOST = "host"
CONF_USE_HTTPS = "use_https"
CONF_VERIFY_SSL = "verify_ssl"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SEND_DATA_AS_QUERY = "send_data_as_query"

# Known device types (from FF00)
DEVICE_TYPES = {
    0x32: "i-soft (Leakage Alarm)",
    0x33: "i-soft SAFE+ (with leak guard)",
    0x34: "SOFTwell P",
    0x35: "SOFTwell S",
    0x36: "SOFTwell K",
    0x41: "i-dos eco",
    0x42: "i-soft K SAFE+",
    0x43: "i-soft K (Leakage Alarm)",
    0x44: "ZEWA i-SAFE / FILT / PROM-i-SAFE",
    0x47: "SOFTwell KP",
    0x48: "SOFTwell KS",
    0x4B: "i-soft PRO (leak guard)",
    0x4C: "i-soft PRO L",
    0x53: "i-soft (Leakage Alarm)",
    0x54: "i-soft K (Leakage Alarm)",
    0x57: "i-soft SAFE+ (var)",
    0x58: "i-soft PRO",
    0x59: "SOFTwell P (var)",
    0x5A: "SOFTwell K (var)",
    0x62: "SOFTwell KP (var)",
    0x63: "SOFTwell S (var)",
    0x64: "SOFTwell KS (var)",
    0x67: "i-soft K SAFE+ (var)",
}