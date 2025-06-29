canonn_patrols_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSMFJL2u0TbLMAQQ5zYixzgjjsNtGunZ9-PPZFheB4xzrjwR0JPPMcdMwqLm8ioVMp3MP4-k-JsIVzO/pub?gid=282559555&single=true&output=csv"
bgs_tasks_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQQZFJ4O0nb3L1WJk5oMEPJrr1w5quBSnPRwSbz66XCYx0Lq6aAexm9s1t8N8iRxpdbUOtrhKqQMayY/pub?gid=0&single=true&output=csv"
edsm_poi_url = "https://www.edsm.net/en/galactic-mapping/json"
edsm_url = "https://www.edsm.net"

#####################
### CEC ENDPOINTS ###
#####################
cec_url = "https://closeencounterscorps.org"
galaxy_url = "https://api-galaxy.closeencounterscorps.org"

###################
### CANONN URLS ###
###################
canonn_cloud_url_us_central = "https://us-central1-canonn-api-236217.cloudfunctions.net"
canonn_cloud_url_europe_west = "https://europe-west1-canonn-api-236217.cloudfunctions.net"

ships = {  #Некоторые корабли имеют "а" перед названием, потому что этот словарь используется  для подстановки типов в сообщение с учетом женского рода
    "adder": " Adder",
    "typex_3": " Alliance Challenger",
    "typex": " Alliance Chieftain",
    "typex_2": " Alliance Crusader",
    "anaconda": "а Anaconda",
    "asp explorer": " Asp Explorer",
    "asp": " Asp Explorer",
    "asp scout": " Asp Scout",
    "asp_scout": " Asp Scout",
    "beluga liner": "а Beluga Liner",
    "belugaliner": "а Beluga Liner",
    "cobra mk. iii": "а Cobra MkIII",
    "cobramkiii": "а Cobra MkIII",
    "cobra mk. iv": "а Cobra MkIV",
    "cobramkiv": "а Cobra MkIV",
    "diamondback explorer": " Diamondback Explorer",
    "diamondbackxl": " Diamondback Explorer",
    "diamondback scout": " Diamondback Scout",
    "diamondback": " Diamondback Scout",
    "dolphin": " Dolphin",
    "eagle": " Eagle",
    "federal assault ship": " Federal Assault Ship",
    "federation_dropship_mkii": " Federal Assault Ship",
    "federal corvette": " Federal Corvette",
    "federation_corvette": " Federal Corvette",
    "federal dropship": " Federal Dropship",
    "federation_dropship": " Federal Dropship",
    "federal gunship": " Federal Gunship",
    "federation_gunship": " Federal Gunship",
    "fer-de-lance": " Fer-de-Lance",
    "ferdelance": " Fer-de-Lance",
    "hauler": " Hauler",
    "imperial clipper": " Imperial Clipper",
    "empire_trader": " Imperial Clipper",
    "imperial courier": " Imperial Courier",
    "empire_courier": " Imperial Courier",
    "imperial cutter": " Imperial Cutter",
    "cutter": " Imperial Cutter",
    "empire_eagle": " Imperial Eagle",
    "keelback": " Keelback",
    "independant_trader": " Keelback",  # ???
    "krait_mkii": " Krait MkII",
    "krait_light": " Krait Phantom",
    "mamba": "а Mamba",
    "orca": "а Orca",
    "python": " Python",
    "sidewinder": " Sidewinder",
    "type 6 transporter": " Type-6 Transporter",
    "type6": " Type-6 Transporter",
    "type 7 transporter": " Type-7 Transporter",
    "type7": " Type-7 Transporter",
    "type 9 heavy": " Type-9 Heavy",
    "type9": " Type-9 Heavy",
    "type 10 defender": " Type-10 Defender",
    "type9_military": " Type-10 Defender",
    "viper mk. iii": " Viper MkIII",
    "viper": " Viper MkIII",
    "viper mk. iv": " Viper MkIV",
    "viper_mkiv": " Viper MkIV",
    "vulture": "а Vulture",
}

states = {
    "civilliberty": "Гражданские свободы",
    "none": "Нет данных",
    "boom": "Бум",
    "bust": "Спад",
    "civilunrest": "Гражданские беспорядки",
    "civilwar": "Гражданская война",
    "election": "Выборы",
    "expansion": "Экспансия",
    "famine": "Голод",
    "investment": "Инвестиции",
    "lockdown": "Изоляция",
    "outbreak": "Эпидемия",
    "retreat": "Отступление",
    "war": "Война",
}

odyssey_events = [
    "BookDropship",
    "BookTaxi",
    "BuyMicroResources",
    "BuySuit",
    "BuyWeapon",
    "CollectItems",
    "CreateSuitLoadout",
    "DeleteSuitLoadout",
    "DropShipDeploy",
    "Disembark",
    "Embark",
    "FCMaterials",
    "LoadoutEquipModule",
    "LoadoutRemoveModule",
    "RenameSuitLoadout",
    "ScanOrganic",
    "SellMicroResources",
    "SellOrganicData",
    "SellSuit",
    "SellWeapon",
    "SwitchSuitLoadout",
    "TransferMicroResources",
    "TradeMicroResources",
    "UpgradeWeapon",
]

poi_categories = [
    "Anomaly",
    "Biology",
    "Cloud",
    "Geology",
    "Guardian",
    "Human",
    "Other",
    "Planets",
    "Ring",
    "Thargoid",
    "Tourist",
    "None"
]


#############
### other ###
#############
version = "1.12.0-beta-2.hf5"     # семантическое версионирование


try:
    from settings_local import *
except ImportError:
    pass
