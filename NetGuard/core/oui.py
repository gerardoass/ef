"""
core/oui.py
-----------
Base OUI + heuristicas de fingerprinting (hostname, puertos, MAC random).
"""
from __future__ import annotations

OUI: dict[str, tuple[str, str]] = {
    "001CDF": ("Belkin", "router"), "002275": ("Belkin", "router"),
    "14CC20": ("TP-Link", "router"), "50C7BF": ("TP-Link", "router"),
    "60A4B7": ("TP-Link", "router"), "9C5322": ("TP-Link", "router"),
    "AC84C6": ("TP-Link", "router"), "C46E1F": ("TP-Link", "router"),
    "EC086B": ("TP-Link", "router"), "1027F5": ("TP-Link", "router"),
    "A42BB0": ("TP-Link", "router"), "003192": ("Netgear", "router"),
    "20E52A": ("Netgear", "router"), "9CD36D": ("Netgear", "router"),
    "A040A0": ("Netgear", "router"), "C40415": ("Netgear", "router"),
    "001E2A": ("Netgear", "router"), "2C3033": ("Netgear", "router"),
    "44A56E": ("Netgear", "router"), "0024B2": ("Netgear", "router"),
    "0026F2": ("Netgear", "router"), "B03956": ("Netgear", "router"),
    "001349": ("ZyXEL", "router"), "5CE28C": ("ZyXEL", "router"),
    "001CB3": ("Apple", "router"), "F0F61C": ("Apple", "router"),
    "0024B1": ("ARRIS", "router"), "44E9DD": ("Sagemcom", "router"),
    "94A408": ("Sagemcom", "router"), "F492BF": ("Ubiquiti", "router"),
    "245A4C": ("Ubiquiti", "router"), "788A20": ("Ubiquiti", "router"),
    "B4FBE4": ("Ubiquiti", "router"), "68D79A": ("Ubiquiti", "router"),
    "C0C9E3": ("Huawei", "router"), "283152": ("Huawei", "router"),
    "7C6097": ("Huawei", "router"), "80717A": ("Huawei", "router"),
    "00E0FC": ("Huawei", "router"), "0018E7": ("Huawei", "router"),
    "444E1A": ("Xiaomi", "router"), "64B473": ("Xiaomi", "router"),
    "F0B429": ("Xiaomi", "router"), "8CDE52": ("ASUS", "router"),
    "2C56DC": ("ASUS", "router"), "1C872C": ("ASUS", "router"),
    "50465D": ("ASUS", "router"), "AC220B": ("ASUS", "router"),
    "D850E6": ("ASUS", "router"), "0024A5": ("Buffalo", "router"),
    "000D0B": ("Buffalo", "router"), "0022B0": ("D-Link", "router"),
    "1CBDB9": ("D-Link", "router"), "340804": ("D-Link", "router"),
    "9094E4": ("D-Link", "router"), "C8D719": ("D-Link", "router"),
    "F07D68": ("D-Link", "router"), "001C10": ("Cisco-Linksys", "router"),
    "001A70": ("Cisco-Linksys", "router"), "C0C1C0": ("Cisco-Linksys", "router"),
    "48F8B3": ("Linksys", "router"), "94103E": ("Belkin", "router"),
    "744401": ("Netgear", "router"), "E091F5": ("Netgear", "router"),
    "001F33": ("Netgear", "router"), "40 5D 82": ("Netgear", "router"),
    "C025E9": ("TP-Link", "router"), "30B5C2": ("TP-Link", "router"),
    "94103E2": ("Belkin", "router"),

    "0017E9": ("Apple", "phone"), "001B63": ("Apple", "phone"),
    "0021E9": ("Apple", "phone"), "002500": ("Apple", "phone"),
    "0026BB": ("Apple", "phone"), "3C0754": ("Apple", "phone"),
    "40D32D": ("Apple", "phone"), "5C969D": ("Apple", "phone"),
    "64B9E8": ("Apple", "phone"), "7CD1C3": ("Apple", "phone"),
    "8C8590": ("Apple", "phone"), "A4C361": ("Apple", "phone"),
    "AC61EA": ("Apple", "phone"), "B8C75D": ("Apple", "phone"),
    "D0E140": ("Apple", "phone"), "DC2B2A": ("Apple", "phone"),
    "F0DBF8": ("Apple", "phone"), "F8FFC2": ("Apple", "phone"),
    "0012FB": ("Samsung", "phone"), "002339": ("Samsung", "phone"),
    "1C5A3E": ("Samsung", "phone"), "2C4401": ("Samsung", "phone"),
    "38AA3C": ("Samsung", "phone"), "4C3C16": ("Samsung", "phone"),
    "50CCF8": ("Samsung", "phone"), "5CE8EB": ("Samsung", "phone"),
    "68EBAE": ("Samsung", "phone"), "78ABBB": ("Samsung", "phone"),
    "8C71F8": ("Samsung", "phone"), "A02195": ("Samsung", "phone"),
    "AC5F3E": ("Samsung", "phone"), "BC20A4": ("Samsung", "phone"),
    "D0176A": ("Samsung", "phone"), "E8508B": ("Samsung", "phone"),
    "F409D8": ("Samsung", "phone"), "FCA13E": ("Samsung", "phone"),
    "0C1DAF": ("Xiaomi", "phone"), "1C4D70": ("Xiaomi", "phone"),
    "28E31F": ("Xiaomi", "phone"), "34CE00": ("Xiaomi", "phone"),
    "50EC50": ("Xiaomi", "phone"), "64CC2E": ("Xiaomi", "phone"),
    "74C63B": ("Xiaomi", "phone"), "8CBEBE": ("Xiaomi", "phone"),
    "9C99A0": ("Xiaomi", "phone"), "B0E235": ("Xiaomi", "phone"),
    "D4970B": ("Xiaomi", "phone"), "F8A45F": ("Xiaomi", "phone"),
    "18FE34": ("OnePlus", "phone"), "34F0CA": ("OnePlus", "phone"),
    "64A2F9": ("OnePlus", "phone"), "94E23C": ("OnePlus", "phone"),
    "C0EEFB": ("OnePlus", "phone"), "3C5AB4": ("Google", "phone"),
    "94EB2C": ("Google", "phone"), "A47733": ("Google", "phone"),
    "F4F5D8": ("Google", "phone"), "00E0B0": ("Huawei", "phone"),
    "1C1D67": ("Huawei", "phone"), "24DBAC": ("Huawei", "phone"),
    "48DB50": ("Huawei", "phone"), "84A8E4": ("Huawei", "phone"),
    "9C28EF": ("Huawei", "phone"), "D4C1C8": ("Huawei", "phone"),
    "E0247F": ("Huawei", "phone"),

    "0024D7": ("Intel", "laptop"), "34E12D": ("Intel", "laptop"),
    "7CB0C2": ("Intel", "laptop"), "94C691": ("Intel", "laptop"),
    "A0A8CD": ("Intel", "laptop"), "E4A471": ("Intel", "laptop"),
    "0022FB": ("Intel", "laptop"), "3C970E": ("Wistron", "laptop"),
    "8CEA48": ("Wistron", "laptop"), "001E64": ("Intel", "laptop"),
    "0024BE": ("Dell", "laptop"), "14FEB5": ("Dell", "laptop"),
    "18DBF2": ("Dell", "laptop"), "24B6FD": ("Dell", "laptop"),
    "34E6D7": ("Dell", "laptop"), "44A842": ("Dell", "laptop"),
    "5C260A": ("Dell", "laptop"), "8CEC4B": ("Dell", "laptop"),
    "B083FE": ("Dell", "laptop"), "D4BED9": ("Dell", "laptop"),
    "F8B156": ("Dell", "laptop"), "F8BC12": ("Dell", "laptop"),
    "0021CC": ("Lenovo", "laptop"), "68F728": ("Lenovo", "laptop"),
    "7CD30A": ("Lenovo", "laptop"), "B888E3": ("Lenovo", "laptop"),
    "E86A64": ("Lenovo", "laptop"), "F0761C": ("Lenovo", "laptop"),
    "001E37": ("HP", "laptop"), "10604B": ("HP", "laptop"),
    "2C27D7": ("HP", "laptop"), "3464A9": ("HP", "laptop"),
    "3CD92B": ("HP", "laptop"), "6CC217": ("HP", "laptop"),
    "9457A5": ("HP", "laptop"), "A0481C": ("HP", "laptop"),
    "B05ADA": ("HP", "laptop"), "D48564": ("HP", "laptop"),
    "E4E749": ("HP", "laptop"), "F4CE46": ("HP", "laptop"),
    "00269E": ("ASUS", "laptop"), "2C4D54": ("ASUS", "laptop"),
    "38D547": ("ASUS", "laptop"), "74D02B": ("ASUS", "laptop"),
    "AC9E17": ("ASUS", "laptop"), "BCAEC5": ("ASUS", "laptop"),
    "D017C2": ("ASUS", "laptop"), "00247E": ("Acer", "laptop"),
    "208984": ("Acer", "laptop"), "40F2E9": ("Acer", "laptop"),
    "680715": ("Acer", "laptop"), "8871B1": ("Acer", "laptop"),
    "C04A00": ("Acer", "laptop"), "00215C": ("Toshiba", "laptop"),
    "B86B23": ("Toshiba", "laptop"), "00238B": ("MSI", "laptop"),
    "4CCC6A": ("MSI", "laptop"), "002264": ("Micro-Star", "laptop"),

    "0017EE": ("Sony", "console"), "7C0E0D": ("Sony", "console"),
    "F8461C": ("Sony", "console"), "98B6E9": ("Nintendo", "console"),
    "58BDA0": ("Nintendo", "console"), "7CBB8A": ("Nintendo", "console"),
    "9CE635": ("Nintendo", "console"), "0009BF": ("Nintendo", "console"),
    "8CCDE8": ("Nintendo", "console"), "002659": ("Microsoft", "console"),
    "6045BD": ("Microsoft", "console"), "7CED8D": ("Microsoft", "console"),
    "985FD3": ("Microsoft", "console"), "C83F26": ("Microsoft", "console"),
    "00125A": ("Microsoft", "console"), "D48A39": ("Google", "tv"),
    "F4F5E8": ("Google", "tv"), "1CF29A": ("Google", "tv"),
    "6CADF8": ("Google", "tv"), "B0C4E7": ("Amazon", "tv"),
    "44650D": ("Amazon", "tv"), "6854FD": ("Amazon", "tv"),
    "74C246": ("Amazon", "tv"), "F0D2F1": ("Amazon", "tv"),
    "8CAE4C": ("Roku", "tv"), "AC3A7A": ("Roku", "tv"),
    "B0A737": ("Roku", "tv"), "D83134": ("Roku", "tv"),

    "2C3AE8": ("Espressif", "iot"), "3C6105": ("Espressif", "iot"),
    "5CCF7F": ("Espressif", "iot"), "600194": ("Espressif", "iot"),
    "A4CF12": ("Espressif", "iot"), "B4E62D": ("Espressif", "iot"),
    "CC50E3": ("Espressif", "iot"), "DC4F22": ("Espressif", "iot"),
    "ECFABC": ("Espressif", "iot"), "246F28": ("Espressif", "iot"),
    "84F3EB": ("Espressif", "iot"), "68C63A": ("Espressif", "iot"),
    "8CAAB5": ("Espressif", "iot"), "B0B21C": ("Philips Hue", "iot"),
    "001788": ("Philips Hue", "iot"), "ECB5FA": ("Philips Hue", "iot"),
    "D8D5B9": ("Sonoff", "iot"), "D4F547": ("Sonoff", "iot"),
    "B827EB": ("Raspberry Pi", "iot"), "DCA632": ("Raspberry Pi", "iot"),
    "E45F01": ("Raspberry Pi", "iot"), "2CCF67": ("Raspberry Pi", "iot"),
    "18B430": ("Nest", "iot"), "641666": ("Nest", "iot"),
    "3C2EF9": ("Wyze", "iot"), "7C78B2": ("Wyze", "iot"),
    "D03F27": ("Wyze", "iot"), "2CAA8E": ("Wyze", "iot"),
    "4C11BF": ("Hikvision", "iot"), "4419B6": ("Hikvision", "iot"),
    "C056E3": ("Hikvision", "iot"), "BCAD28": ("Hikvision", "iot"),
    "3CEF8C": ("Dahua", "iot"), "9C8ECD": ("Amcrest", "iot"),

    "001E0B": ("HP", "printer"), "9CB654": ("HP", "printer"),
    "000048": ("Seiko Epson", "printer"), "44D244": ("Epson", "printer"),
    "A4EE57": ("Epson", "printer"), "001BA9": ("Brother", "printer"),
    "30055C": ("Brother", "printer"), "008077": ("Brother", "printer"),
    "3C2AF4": ("Brother", "printer"), "000085": ("Canon", "printer"),
    "2C9EFC": ("Canon", "printer"), "888717": ("Canon", "printer"),
    "00215A": ("Lexmark", "printer"), "002404": ("Lexmark", "printer"),

    "00155D": ("Hyper-V", "server"), "005056": ("VMware", "server"),
    "080027": ("VirtualBox", "server"), "525400": ("QEMU/KVM", "server"),
    "001132": ("Synology", "server"), "001E06": ("QNAP", "server"),
    "245EBE": ("QNAP", "server"), "000C29": ("VMware", "server"),
    "0242AC": ("Docker", "server"), "00089B": ("ICP", "server"),
}

CATEGORY_LABEL = {
    "router": "ROUTER", "phone": "MOVIL", "laptop": "LAPTOP",
    "desktop": "PC", "console": "CONSOLA", "tv": "SMART TV",
    "iot": "IOT", "printer": "IMPRESORA", "server": "SERVIDOR",
    "unknown": "DESCONOCIDO",
}

RANDOM_LABEL = "MAC ALEATORIA"


def normalize_mac(mac: str) -> str:
    h = "".join(c for c in (mac or "").upper() if c in "0123456789ABCDEF")
    if len(h) < 12:
        return (mac or "").upper()
    h = h[:12]
    return ":".join(h[i:i + 2] for i in range(0, 12, 2))


def is_randomized(mac: str) -> bool:
    try:
        return bool(int(normalize_mac(mac).split(":")[0], 16) & 0b10)
    except Exception:
        return False


def is_multicast(mac: str) -> bool:
    try:
        return bool(int(normalize_mac(mac).split(":")[0], 16) & 0b1)
    except Exception:
        return False


def lookup_vendor(mac: str) -> tuple[str, str]:
    if not mac or mac.startswith(("00:00:00", "FF:FF:FF")):
        return ("Desconocido", "unknown")
    if is_randomized(mac):
        return (RANDOM_LABEL, "unknown")
    h = normalize_mac(mac).replace(":", "")
    for size in (6, 7):
        if h[:size] in OUI:
            return OUI[h[:size]]
    for k, v in OUI.items():
        if h.startswith(k.replace(" ", "")):
            return v
    return ("Desconocido", "unknown")


HOST_RULES: list[tuple[tuple[str, ...], str]] = [
    (("iphone", "ipad", "android", "galaxy", "redmi", "poco", "pixel", "oneplus",
      "xiaomi", "sm-", "moto", "honor", "oppo", "vivo", "realme", "huawei-p",
      "iphone-de", "s21", "s22", "s23"), "phone"),
    (("macbook", "laptop", "notebook", "thinkpad", "ideapad", "vivobook", "zenbook",
      "pavilion", "inspiron", "latitude", "elitebook", "probook", "aspire", "swift-",
      "surface", "legion", "nitro", "predator", "victus", "omen"), "laptop"),
    (("desktop", "-pc", "pc-", "workstation", "tower", "rig", "gamer", "ryzen"), "desktop"),
    (("router", "gateway", "gw-", "fritz", "archer", "deco", "orbi", "eero", "amplifi",
      "velop", "repeater", "extender", "mesh", "livebox", "movistar", "vodafone",
      "orange", "comtrend", "mitrastar", "homehub", "technicolor", "sagemcom",
      "zyxel", "hg8", "hg6", "ont"), "router"),
    (("printer", "hp-", "epson", "brother", "canon", "lexmark", "deskjet",
      "laserjet", "officejet", "mfc-", "dcp-"), "printer"),
    (("tv", "bravia", "webos", "tizen", "chromecast", "googletv", "firetv",
      "fire-tv", "roku", "appletv", "shield", "androidtv", "smart-tv"), "tv"),
    (("ps4", "ps5", "playstation", "xbox", "switch", "nintendo"), "console"),
    (("nas", "synology", "qnap", "diskstation", "readynas", "truenas", "server",
      "srv-", "proxmox", "esxi"), "server"),
    (("esp", "shelly", "sonoff", "tasmota", "hue", "alexa", "echo", "nest",
      "tuya", "zigbee", "smart-"), "iot"),
]

PORT_SIG: list[tuple[tuple[int, ...], str]] = [
    ((62078,), "phone"), ((5555,), "phone"),
    ((7547,), "router"), ((53, 80), "router"), ((53, 443), "router"),
    ((9100, 515, 631), "printer"),
    ((3389,), "desktop"), ((445, 139), "laptop"),
    ((8009, 8008), "tv"), ((32400, 5000), "server"), ((1883, 8883), "iot"),
]


def from_hostname(hostname: str | None) -> str | None:
    if not hostname:
        return None
    h = hostname.lower()
    for kws, cat in HOST_RULES:
        if any(k in h for k in kws):
            return cat
    return None


def from_ports(ports: list[int]) -> str | None:
    p = set(ports)
    for sig, cat in PORT_SIG:
        if p & set(sig):
            return cat
    return None