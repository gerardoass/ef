"""
core/oui.py
-----------
Base OUI compacta (prefijos MAC -> fabricante/categoria) mas
heuristicas de clasificacion. No pretende ser exhaustiva: cubre los
fabricantes que realmente aparecen en una LAN domestica.
"""
from __future__ import annotations

# prefijo (6 hex sin separador) -> (fabricante, categoria)
OUI: dict[str, tuple[str, str]] = {
    # --- Routers / CPE / mesh ---
    "001CDF": ("Belkin", "router"),      "002275": ("Belkin", "router"),
    "14CC20": ("TP-Link", "router"),     "50C7BF": ("TP-Link", "router"),
    "60A4B7": ("TP-Link", "router"),     "9C5322": ("TP-Link", "router"),
    "AC84C6": ("TP-Link", "router"),     "C46E1F": ("TP-Link", "router"),
    "EC086B": ("TP-Link", "router"),     "1027F5": ("TP-Link", "router"),
    "A42BB0": ("TP-Link", "router"),     "003192": ("Netgear", "router"),
    "20E52A": ("Netgear", "router"),     "9CD36D": ("Netgear", "router"),
    "A040A0": ("Netgear", "router"),     "C40415": ("Netgear", "router"),
    "001E2A": ("Netgear", "router"),     "2C3033": ("Netgear", "router"),
    "44A56E": ("Netgear", "router"),     "0024B2": ("Netgear", "router"),
    "0026F2": ("Netgear", "router"),     "B03956": ("Netgear", "router"),
    "001349": ("ZyXEL", "router"),       "5CE28C": ("ZyXEL", "router"),
    "001CB3": ("Apple", "router"),       "F0F61C": ("Apple", "router"),
    "0024B1": ("ARRIS", "router"),       "44E9DD": ("Sagemcom", "router"),
    "94A408": ("Sagemcom", "router"),    "F492BF": ("Ubiquiti", "router"),
    "245A4C": ("Ubiquiti", "router"),    "788A20": ("Ubiquiti", "router"),
    "B4FBE4": ("Ubiquiti", "router"),    "68D79A": ("Ubiquiti", "router"),
    "00408C": ("Asterisk", "router"),    "C0C9E3": ("Huawei", "router"),
    "283152": ("Huawei", "router"),      "7C6097": ("Huawei", "router"),
    "80717A": ("Huawei", "router"),      "00E0FC": ("Huawei", "router"),
    "0018E7": ("Huawei", "router"),      "5CA6E6": ("Huawei", "router"),
    "444E1A": ("Xiaomi", "router"),      "64B473": ("Xiaomi", "router"),
    "78 11 DC": ("Xiaomi", "router"),    "F0B429": ("Xiaomi", "router"),
    "8CDE52": ("ASUS", "router"),        "2C56DC": ("ASUS", "router"),
    "1C872C": ("ASUS", "router"),        "50465D": ("ASUS", "router"),
    "00 1B FC": ("ASUS", "router"),      "AC220B": ("ASUS", "router"),
    "D850E6": ("ASUS", "router"),        "0024A5": ("Buffalo", "router"),
    "000D0B": ("Buffalo", "router"),     "001601": ("Buffalo", "router"),
    "0022B0": ("D-Link", "router"),      "1CBDB9": ("D-Link", "router"),
    "340804": ("D-Link", "router"),      "9094E4": ("D-Link", "router"),
    "C8D719": ("D-Link", "router"),      "F07D68": ("D-Link", "router"),
    "001C10": ("Cisco-Linksys", "router"),
    "001A70": ("Cisco-Linksys", "router"),
    "C0C1C0": ("Cisco-Linksys", "router"),
    "48F8B3": ("Linksys", "router"),     "94103E": ("Belkin", "router"),
    "744401": ("Netgear", "router"),     "84 1B 5E": ("Netgear", "router"),
    "E091F5": ("Netgear", "router"),     "40 5D 82": ("Netgear", "router"),
    "001F33": ("Netgear", "router"),     "E8 4F 25": ("Huawei", "router"),
    "94 04 9C": ("Huawei", "router"),    "C8 94 BB": ("Huawei", "router"),
    "C0 25 E9": ("TP-Link", "router"),   "30 B5 C2": ("TP-Link", "router"),

    # --- Moviles ---
    "0017E9": ("Apple", "phone"),        "001B63": ("Apple", "phone"),
    "0021E9": ("Apple", "phone"),        "002500": ("Apple", "phone"),
    "0026BB": ("Apple", "phone"),        "3C0754": ("Apple", "phone"),
    "40D32D": ("Apple", "phone"),        "5C969D": ("Apple", "phone"),
    "64B9E8": ("Apple", "phone"),        "7CD1C3": ("Apple", "phone"),
    "8C8590": ("Apple", "phone"),        "A4C361": ("Apple", "phone"),
    "AC61EA": ("Apple", "phone"),        "B8C75D": ("Apple", "phone"),
    "D0E140": ("Apple", "phone"),        "DC2B2A": ("Apple", "phone"),
    "F0DBF8": ("Apple", "phone"),        "F8FFC2": ("Apple", "phone"),
    "0012FB": ("Samsung", "phone"),      "002339": ("Samsung", "phone"),
    "1C5A3E": ("Samsung", "phone"),      "2C4401": ("Samsung", "phone"),
    "38AA3C": ("Samsung", "phone"),      "4C3C16": ("Samsung", "phone"),
    "50CCF8": ("Samsung", "phone"),      "5CE8EB": ("Samsung", "phone"),
    "68EBAE": ("Samsung", "phone"),      "78ABBB": ("Samsung", "phone"),
    "8C71F8": ("Samsung", "phone"),      "A02195": ("Samsung", "phone"),
    "AC5F3E": ("Samsung", "phone"),      "BC20A4": ("Samsung", "phone"),
    "D0176A": ("Samsung", "phone"),      "E8508B": ("Samsung", "phone"),
    "F409D8": ("Samsung", "phone"),      "FCA13E": ("Samsung", "phone"),
    "0C1DAF": ("Xiaomi", "phone"),       "1C4D70": ("Xiaomi", "phone"),
    "28E31F": ("Xiaomi", "phone"),       "34CE00": ("Xiaomi", "phone"),
    "50EC50": ("Xiaomi", "phone"),       "64CC2E": ("Xiaomi", "phone"),
    "74C63B": ("Xiaomi", "phone"),       "8CBEBE": ("Xiaomi", "phone"),
    "9C99A0": ("Xiaomi", "phone"),       "A8 9C ED": ("Xiaomi", "phone"),
    "B0E235": ("Xiaomi", "phone"),       "D4970B": ("Xiaomi", "phone"),
    "F0B429": ("Xiaomi", "phone"),       "F8A45F": ("Xiaomi", "phone"),
    "18FE34": ("OnePlus", "phone"),      "34F0CA": ("OnePlus", "phone"),
    "64A2F9": ("OnePlus", "phone"),      "94E23C": ("OnePlus", "phone"),
    "C0EEFB": ("OnePlus", "phone"),      "3C5AB4": ("Google", "phone"),
    "54 60 09": ("Google", "phone"),     "94EB2C": ("Google", "phone"),
    "A47733": ("Google", "phone"),       "F4F5D8": ("Google", "phone"),
    "00E0B0": ("Huawei", "phone"),       "1C1D67": ("Huawei", "phone"),
    "24DBAC": ("Huawei", "phone"),       "48DB50": ("Huawei", "phone"),
    "6C 8D C1": ("Huawei", "phone"),     "84A8E4": ("Huawei", "phone"),
    "9C28EF": ("Huawei", "phone"),       "AC E2 15": ("Huawei", "phone"),
    "D4C1C8": ("Huawei", "phone"),       "E0247F": ("Huawei", "phone"),
    "28 6C 07": ("Xiaomi", "phone"),     "00 9E C8": ("Xiaomi", "phone"),

    # --- Portatiles / sobremesa ---
    "0024D7": ("Intel", "laptop"),       "34E12D": ("Intel", "laptop"),
    "7CB0C2": ("Intel", "laptop"),       "94C691": ("Intel", "laptop"),
    "A0A8CD": ("Intel", "laptop"),       "E4A471": ("Intel", "laptop"),
    "0022FB": ("Intel", "laptop"),       "0021 6A": ("Intel", "laptop"),
    "3C970E": ("Wistron", "laptop"),     "8CEA48": ("Wistron", "laptop"),
    "001E64": ("Intel", "laptop"),       "0024BE": ("Dell", "laptop"),
    "14FE B5": ("Dell", "laptop"),       "18DBF2": ("Dell", "laptop"),
    "24B6FD": ("Dell", "laptop"),        "34E6D7": ("Dell", "laptop"),
    "44A842": ("Dell", "laptop"),        "5C260A": ("Dell", "laptop"),
    "78 2B CB": ("Dell", "laptop"),      "8C EC 4B": ("Dell", "laptop"),
    "B083FE": ("Dell", "laptop"),        "D4BED9": ("Dell", "laptop"),
    "F8B156": ("Dell", "laptop"),        "F8BC12": ("Dell", "laptop"),
    "0021CC": ("Lenovo", "laptop"),      "1C 39 47": ("Lenovo", "laptop"),
    "3C 91 80": ("Lenovo", "laptop"),    "54 5E BD": ("Lenovo", "laptop"),
    "68F728": ("Lenovo", "laptop"),      "7CD30A": ("Lenovo", "laptop"),
    "9C B6 D0": ("Lenovo", "laptop"),    "B8 88 E3": ("Lenovo", "laptop"),
    "E8 6A 64": ("Lenovo", "laptop"),    "F0 76 1C": ("Lenovo", "laptop"),
    "00 1E 37": ("HP", "laptop"),        "10 60 4B": ("HP", "laptop"),
    "2C 27 D7": ("HP", "laptop"),        "34 64 A9": ("HP", "laptop"),
    "3C D9 2B": ("HP", "laptop"),        "6C C2 17": ("HP", "laptop"),
    "94 57 A5": ("HP", "laptop"),        "A0 48 1C": ("HP", "laptop"),
    "B0 5A DA": ("HP", "laptop"),        "D4 85 64": ("HP", "laptop"),
    "E4 E7 49": ("HP", "laptop"),        "F4 CE 46": ("HP", "laptop"),
    "00 26 9E": ("ASUS", "laptop"),      "2C 4D 54": ("ASUS", "laptop"),
    "38 D5 47": ("ASUS", "laptop"),      "50 46 5D": ("ASUS", "laptop"),
    "74 D0 2B": ("ASUS", "laptop"),      "AC 9E 17": ("ASUS", "laptop"),
    "BC AE C5": ("ASUS", "laptop"),      "D0 17 C2": ("ASUS", "laptop"),
    "00 24 7E": ("Acer", "laptop"),      "20 89 84": ("Acer", "laptop"),
    "40 F2 E9": ("Acer", "laptop"),      "68 07 15": ("Acer", "laptop"),
    "88 71 B1": ("Acer", "laptop"),      "C0 4A 00": ("Acer", "laptop"),
    "00 21 5C": ("Toshiba", "laptop"),   "B8 6B 23": ("Toshiba", "laptop"),
    "00 23 8B": ("MSI", "laptop"),       "4C CC 6A": ("MSI", "laptop"),
    "00 22 64": ("Micro-Star", "laptop"),

    # --- Consolas / TV / streaming ---
    "0017EE": ("Sony", "console"),       "7C0E0D": ("Sony", "console"),
    "F8461C": ("Sony", "console"),       "BC 60 10": ("Sony", "console"),
    "98B6E9": ("Nintendo", "console"),   "58BDA0": ("Nintendo", "console"),
    "7CBB8A": ("Nintendo", "console"),   "9CE635": ("Nintendo", "console"),
    "0009BF": ("Nintendo", "console"),   "8CCDE8": ("Nintendo", "console"),
    "0017AB": ("Nintendo", "console"),   "002659": ("Microsoft", "console"),
    "60 45 BD": ("Microsoft", "console"),"7C ED 8D": ("Microsoft", "console"),
    "98 5F D3": ("Microsoft", "console"),"C8 3F 26": ("Microsoft", "console"),
    "00125A": ("Microsoft", "console"),  "D4 8A 39": ("Google", "tv"),
    "F4F5E8": ("Google", "tv"),          "1C F2 9A": ("Google", "tv"),
    "6C AD F8": ("Google", "tv"),        "B0C4E7": ("Amazon", "tv"),
    "44 65 0D": ("Amazon", "tv"),        "68 54 FD": ("Amazon", "tv"),
    "74C246": ("Amazon", "tv"),          "F0 D2 F1": ("Amazon", "tv"),
    "8CAE4C": ("Roku", "tv"),            "AC3A7A": ("Roku", "tv"),
    "B0 A7 37": ("Roku", "tv"),          "D8 31 34": ("Roku", "tv"),
    "00 1A 11": ("Google", "tv"),        "D8 6C 63": ("Google", "tv"),

    # --- IoT / domotica / camaras ---
    "2C3AE8": ("Espressif", "iot"),      "3C6105": ("Espressif", "iot"),
    "5CCF7F": ("Espressif", "iot"),      "600194": ("Espressif", "iot"),
    "A4CF12": ("Espressif", "iot"),      "B4E62D": ("Espressif", "iot"),
    "CC50E3": ("Espressif", "iot"),      "DC4F22": ("Espressif", "iot"),
    "ECFABC": ("Espressif", "iot"),      "246F28": ("Espressif", "iot"),
    "84F3EB": ("Espressif", "iot"),      "48 3F DA": ("Espressif", "iot"),
    "68C63A": ("Espressif", "iot"),      "8CAAB5": ("Espressif", "iot"),
    "B0B21C": ("Philips Hue", "iot"),    "001788": ("Philips Hue", "iot"),
    "ECB5FA": ("Philips Hue", "iot"),    "D8D5B9": ("Sonoff", "iot"),
    "84 0D 8E": ("Espressif", "iot"),    "D4F547": ("Sonoff", "iot"),
    "A0 20 A6": ("Espressif", "iot"),    "F4CFA2": ("Espressif", "iot"),
    "3C 71 BF": ("Espressif", "iot"),    "7CDFA1": ("Espressif", "iot"),
    "18FE34": ("Espressif", "iot"),      "C4 4F 33": ("Espressif", "iot"),
    "9C 9C 1E": ("Espressif", "iot"),    "44 17 93": ("Espressif", "iot"),
    "001A79": ("Teledatics", "iot"),     "F0 9F C2": ("Ubiquiti", "iot"),
    "B827EB": ("Raspberry Pi", "iot"),   "DCA632": ("Raspberry Pi", "iot"),
    "E45F01": ("Raspberry Pi", "iot"),   "2CCF67": ("Raspberry Pi", "iot"),
    "D8 3A DD": ("Raspberry Pi", "iot"), "88 A2 9E": ("Raspberry Pi", "iot"),
    "00 1E C0": ("Microchip", "iot"),    "00 04 A3": ("Microchip", "iot"),
    "18B430": ("Nest", "iot"),           "641666": ("Nest", "iot"),
    "6C AD F8": ("Google Nest", "iot"),  "F4F5D8": ("Google Nest", "iot"),
    "3C2EF9": ("Wyze", "iot"),           "7C78B2": ("Wyze", "iot"),
    "D03F27": ("Wyze", "iot"),           "2CAA8E": ("Wyze", "iot"),
    "9C 8E CD": ("Amcrest", "iot"),      "3C EF 8C": ("Dahua", "iot"),
    "4C 11 BF": ("Hikvision", "iot"),    "44 19 B6": ("Hikvision", "iot"),
    "C0 56 E3": ("Hikvision", "iot"),    "BC AD 28": ("Hikvision", "iot"),

    # --- Impresoras ---
    "00 1E 0B": ("HP", "printer"),       "3C D9 2B": ("HP", "printer"),
    "9C B6 54": ("HP", "printer"),       "B0 5A DA": ("HP", "printer"),
    "00 00 48": ("Seiko Epson", "printer"),
    "44 D2 44": ("Epson", "printer"),    "A4 EE 57": ("Epson", "printer"),
    "00 1B A9": ("Brother", "printer"),  "30 05 5C": ("Brother", "printer"),
    "00 80 77": ("Brother", "printer"),  "3C 2A F4": ("Brother", "printer"),
    "00 00 85": ("Canon", "printer"),    "2C 9E FC": ("Canon", "printer"),
    "88 87 17": ("Canon", "printer"),    "00 15 99": ("Samsung", "printer"),
    "00 21 5A": ("Lexmark", "printer"),  "00 24 04": ("Lexmark", "printer"),

    # --- Servidores / NAS / virtualizacion ---
    "00 15 5D": ("Microsoft Hyper-V", "server"),
    "00 50 56": ("VMware", "server"),
    "08 00 27": ("VirtualBox", "server"),
    "52 54 00": ("QEMU/KVM", "server"),
    "00 11 32": ("Synology", "server"),  "00 1E 06": ("QNAP", "server"),
    "24 5E BE": ("QNAP", "server"),      "00 08 9B": ("ICP Electronics", "server"),
    "00 0C 29": ("VMware", "server"),    "02 42 AC": ("Docker", "server"),
}

CATEGORY_LABEL = {
    "router":  "Router / AP",
    "phone":   "Smartphone",
    "laptop":  "Portatil",
    "desktop": "PC Sobremesa",
    "console": "Consola",
    "tv":      "Smart TV / Streaming",
    "iot":     "IoT / Domotica",
    "printer": "Impresora",
    "server":  "Servidor / NAS",
    "unknown": "Desconocido",
}

CATEGORY_ICON = {
    "router":  "📡",
    "phone":   "📱",
    "laptop":  "💻",
    "desktop": "🖥",
    "console": "🎮",
    "tv":      "📺",
    "iot":     "🔌",
    "printer": "🖨",
    "server":  "🗄",
    "unknown": "❔",
}


def normalize_mac(mac: str) -> str:
    """Normaliza MAC a XX:XX:XX:XX:XX:XX en mayusculas."""
    hexs = "".join(c for c in mac.upper() if c in "0123456789ABCDEF")
    if len(hexs) < 12:
        return mac.upper()
    hexs = hexs[:12]
    return ":".join(hexs[i:i + 2] for i in range(0, 12, 2))


def is_randomized(mac: str) -> bool:
    """
    MAC aleatoria/privada: bit 'locally administered' activo
    (segundo nibble del primer octeto en {2,6,A,E}).
    Tipico de iOS/Android con MAC randomization activada.
    """
    try:
        first = int(normalize_mac(mac).split(":")[0], 16)
        return bool(first & 0b10)
    except Exception:
        return False


def is_multicast(mac: str) -> bool:
    try:
        first = int(normalize_mac(mac).split(":")[0], 16)
        return bool(first & 0b1)
    except Exception:
        return False


def lookup_vendor(mac: str) -> tuple[str, str]:
    """Devuelve (fabricante, categoria). ('Desconocido','unknown') si falla."""
    if not mac or mac.startswith(("00:00:00", "FF:FF:FF")):
        return ("Desconocido", "unknown")
    if is_randomized(mac):
        return ("MAC aleatoria (privada)", "unknown")

    hexs = normalize_mac(mac).replace(":", "")
    for size in (6, 7):
        hit = OUI.get(hexs[:size])
        if hit:
            return hit
    # Segundo intento con separadores limpios del diccionario
    for key, val in OUI.items():
        k = key.replace(" ", "")
        if hexs.startswith(k):
            return val
    return ("Desconocido", "unknown")


# --- Heuristicas por hostname -----------------------------------------
HOSTNAME_RULES: list[tuple[tuple[str, ...], str]] = [
    (("iphone", "ipad", "android", "galaxy", "redmi", "poco", "pixel",
      "oneplus", "xiaomi", "huawei-p", "sm-", "moto", "honor", "oppo",
      "vivo", "realme", "iphone-de"), "phone"),
    (("macbook", "laptop", "notebook", "thinkpad", "ideapad", "vivobook",
      "zenbook", "pavilion", "inspiron", "latitude", "elitebook",
      "probook", "aspire", "swift-", "surface", "legion", "nitro",
      "predator", "victus", "omen"), "laptop"),
    (("desktop", "-pc", "pc-", "workstation", "tower", "rig", "gamer",
      "ryzen", "intel-core", "msi-", "custom"), "desktop"),
    (("router", "gateway", "gw-", "fritz", "archer", "deco", "orbi",
      "eero", "amplifi", "velop", "repeater", "extender", "mesh",
      "livebox", "movistar", "vodafone", "orange", "comtrend",
      "mitrastar", "homehub", "technicolor", "sagemcom", "huawei-hg",
      "zyxel", "router-"), "router"),
    (("printer", "hp-", "epson", "brother", "canon", "lexmark",
      "deskjet", "laserjet", "officejet", "mfc-", "dcp-"), "printer"),
    (("tv", "bravia", "webos", "tizen", "chromecast", "googletv",
      "firetv", "fire-tv", "roku", "appletv", "shield", "androidtv"), "tv"),
    (("ps4", "ps5", "playstation", "xbox", "switch", "nintendo"), "console"),
    (("nas", "synology", "qnap", "diskstation", "readynas",
      "truenas", "freenas", "server", "srv-", "proxmox", "esxi"), "server"),
    (("esp", "esp32", "esp8266", "shelly", "sonoff", "tasmota",
      "hue", "alexa", "echo", "nest", "tuya", "zigbee", "smart"), "iot"),
]


def guess_category_from_hostname(hostname: str | None) -> str | None:
    if not hostname:
        return None
    h = hostname.lower()
    for keywords, cat in HOSTNAME_RULES:
        for kw in keywords:
            if kw in h:
                return cat
    return None


# --- Heuristicas por puertos abiertos ---------------------------------
PORT_SIGNATURES: list[tuple[tuple[int, ...], str]] = [
    ((62078,), "phone"),          # iPhone lockdownd
    ((5555,), "phone"),           # Android ADB
    ((53, 80, 443), "router"),
    ((53, 7547), "router"),       # TR-069
    ((9100, 515, 631), "printer"),
    ((445, 139, 3389), "desktop"),
    ((445, 139), "laptop"),
    ((8009, 8008), "tv"),         # Chromecast
    ((5000, 32400), "server"),    # Synology DSM / Plex
    ((1883, 8883), "iot"),        # MQTT
]


def guess_category_from_ports(ports: list[int]) -> str | None:
    pset = set(ports)
    for sig, cat in PORT_SIGNATURES:
        if pset & set(sig):
            return cat
    return None