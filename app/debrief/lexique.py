"""Lexique franco-DCS de la fiche de faits -- brief SONNET Lot Récit A §4.

Traduit une clé technique DCS (`target_unit_type` d'un abattage/duel,
`initiator_unit_type` d'un coup) en un libellé lisible, et fournit la
catégorie utilisée par `_group_salves` (§5) pour regrouper des salves
au-delà du type exact.

Trois niveaux de repli, dans cet ordre -- le troisième n'est jamais
contourné (brief §4, avertissement) :
    1. le libellé français de `_LEXIQUE`, s'il est renseigné ;
    2. à défaut, un libellé générique tiré de la catégorie -- celle de
       `_LEXIQUE` si posée, sinon celle de `_CATEGORIE_PAR_CLE`
       (classification par attributs, calculée une fois pour toutes hors
       ligne à partir d'`object_db_v2_index.json`, brief §4) ;
    3. à défaut, la clé brute, telle quelle. JAMAIS une traduction devinée.

`_LEXIQUE` couvre les 19 clés mesurées sur la fixture "Bataille de
Francfort" (`89f20c83-...json`) plus les quatre clés nommées par le brief
comme fuyant dans les récits (`Infantry AK ver3`, `HL_ZU-23`,
`p-19 s-125 sr`, `KAMAZ Truck`) -- 19 après recouvrement, la fixture citant
déjà `Infantry AK ver3` n'étant pas le cas ; `Mi-24P` (Lot Le groupement,
brief §3) porte le compte de 18 à 19 -- voir le rapport de livraison
pour le détail. **Ce lot n'a pas eu accès aux données brutes des trois
autres sessions réelles citées par le brief** (`mission_2707`,
`mission_0607`, `entrainement_Syrie`) -- seule la fixture Francfort était
jointe aux fichiers requis à l'upload. Le dimensionnement mesuré du brief
(42 clés sur les quatre sessions) n'est donc couvert qu'en partie par
`_LEXIQUE` ; **le repli (niveaux 2 et 3) porte le reste**, y compris pour
les 24 clés non mesurées ici. C'est un signalement, pas une impasse : les
trois niveaux sont fonctionnels indépendamment de la taille de `_LEXIQUE`.

`_CATEGORIE_PAR_CLE` classe les 628 clés de la base par un premier attribut
trouvé, dans cet ordre de priorité (celui du brief §4, tel que listé) :
Infantry, Air Defence, Artillery, Tanks, Armed vehicles, Planes,
Helicopters. Une clé sans aucun de ces attributs (troupe de transport,
statique, etc.) n'apparaît pas dans la table -- 166 clés sur 628, mesuré.
Cet ordre résout un recouvrement réel et vérifié : un char (`M-1 Abrams`)
porte À LA FOIS `Tanks` et `Armed vehicles` dans la base -- `Tanks` doit
être vérifié avant `Armed vehicles` pour ne pas classer un char en
"blindé" générique (brief §4, l'exemple `BMP-1` vs `M-1 Abrams` : IFV et
char portent tous deux `Armed vehicles`, seul le second porte `Tanks`).

**Écart signalé vis-à-vis du brief (§7) :** le brief associe `F-14A-135-GR`
(`displayName` vide dans la base) au même repli de niveau 3 (clé brute) que
`Grad FDDM` (clé absente de la base). Mesuré : `F-14A-135-GR` EST présent
dans `object_db_v2_index.json` et y porte l'attribut `Planes` -- il a donc
une catégorie exploitable, et le niveau 2 s'applique (« appareil »), pas le
niveau 3. `Grad FDDM`, lui, est absent de la base : aucune catégorie n'est
calculable, le niveau 3 s'applique bien. Les deux clés sont absentes de
`_LEXIQUE` (aucun libellé spécifique écrit pour l'une ou l'autre) ; c'est
la présence ou non d'une catégorie dans la base qui distingue leur repli,
pas la présence dans `_LEXIQUE`. Comportement volontairement conforme à la
donnée mesurée plutôt qu'à l'exemple du brief -- signalé plutôt qu'absorbé
en silence.

N'appartient PAS aux quatre modules hachés par `revision.ENGINE_REVISION`
(brief §1) : fichier neuf, jamais importé par `engine.py`, `debriefer.py`,
`acmi.py` ni `categorize.py`.
"""
from __future__ import annotations

# --- Niveau 1 : libellés spécifiques -----------------------------------------
# clé DCS -> (libellé français, catégorie). La catégorie posée ici prime sur
# `_CATEGORIE_PAR_CLE` pour cette clé (voir `categorie()`) -- elle permet de
# classer correctement un cas ambigu par attributs bruts, ex. "Soldier
# stinger" porte à la fois `Infantry` et `Air Defence` dans la base ; classé
# ici en Air Defence (c'est une menace antiaérienne, pas un fantassin de
# ligne) plutôt que de dépendre de l'ordre de priorité générique.
_LEXIQUE: dict[str, tuple[str, str]] = {
    # -- mesurées sur la fixture "Bataille de Francfort" --
    "BMP-1": ("BMP-1", "Armed vehicles"),
    "BTR-80": ("BTR-80", "Armed vehicles"),
    "F-16C_50": ("F-16C", "Planes"),
    "F-4E-45MC": ("F-4E", "Planes"),
    "Kub 2P25 ln": ("lanceur SA-6 Kub", "Air Defence"),
    "M-1 Abrams": ("M1 Abrams", "Tanks"),
    "Mi-24P": ("Mi-24P", "Helicopters"),
    "Mi-24V": ("Mi-24V", "Helicopters"),
    "MiG-21Bis": ("MiG-21bis", "Planes"),
    "MiG-29 Fulcrum": ("MiG-29", "Planes"),
    "Mirage-F1BQ": ("Mirage F1", "Planes"),
    "Mirage-F1EE": ("Mirage F1", "Planes"),
    "Soldier stinger": ("tireur Stinger", "Air Defence"),
    "Su-25": ("Su-25", "Planes"),
    "T-55": ("T-55", "Tanks"),
    # -- nommées par le brief §4 comme clés qui fuient dans les récits --
    "Infantry AK ver3": ("fantassin", "Infantry"),
    "HL_ZU-23": ("ZU-23 automotrice", "Air Defence"),
    "p-19 s-125 sr": ("radar P-19", "Air Defence"),
    "KAMAZ Truck": ("camion KAMAZ", "Armed vehicles"),
}

# --- Niveau 2 : libellés génériques par catégorie ----------------------------
# Exactement les sept couples du brief §4, aucun ajouté.
_CATEGORIES_GENERIQUES: dict[str, str] = {
    "Infantry": "fantassin",
    "Air Defence": "pièce antiaérienne",
    "Artillery": "pièce d'artillerie",
    "Tanks": "char",
    "Armed vehicles": "blindé",
    "Planes": "appareil",
    "Helicopters": "hélicoptère",
}


# --- Niveau 2, données : classification par attributs (628 clés, calculée
#     hors ligne depuis object_db_v2_index.json -- jamais embarqué au lot,
#     brief §4 : "ne jamais livrer dans le zip") ------------------------------
#
# Correctif Lot Récit B §5 -- priorité `Air Defence` avant `Infantry` : onze
# clés de la base (Igla, Stinger -- les onze MANPADS, aucune autre) portent
# les deux attributs à la fois ; dix ressortaient en "fantassin" faute de
# cette priorité (la onzième, "Soldier stinger", était déjà corrigée par
# recouvrement explicite dans `_LEXIQUE` ci-dessus). Un tireur MANPAD est une
# menace antiaérienne, jamais un fantassin de ligne -- un fantassin au RPG,
# lui, reste classé `Infantry` (arbitrage du porteur, la distinction ne
# l'intéresse pas). C'est une priorité, pas une liste d'exceptions : les
# MANPADS que DCS ajoutera plus tard porteront la même paire d'attributs et
# devront être corrigés de même lors d'une prochaine régénération de cette
# table depuis `object_db_v2_index.json`.
_CATEGORIE_PAR_CLE: dict[str, str] = {
    '1L13 EWR': 'Air Defence',
    '2B11 mortar': 'Artillery',
    '2S1 Gvozdika': 'Artillery',
    '2S19 Msta': 'Artillery',
    '2S3 Akatsia': 'Artillery',
    '2S6 Tunguska': 'Air Defence',
    '2S9 Nona': 'Artillery',
    '55G6 EWR': 'Air Defence',
    '5p73 s-125 ln': 'Air Defence',
    'A-10A': 'Planes',
    'A-10C': 'Planes',
    'A-10C_2': 'Planes',
    'A-20G': 'Planes',
    'A-50': 'Planes',
    'A6E': 'Planes',
    'AAV7': 'Armed vehicles',
    'AH-1W': 'Helicopters',
    'AH-64A': 'Helicopters',
    'AH-64D': 'Helicopters',
    'AH-64D_BLK_II': 'Helicopters',
    'AJS37': 'Planes',
    'AV8BNA': 'Planes',
    'Allies_Director': 'Air Defence',
    'An-26B': 'Planes',
    'An-30M': 'Planes',
    'B-17G': 'Planes',
    'B-1B': 'Planes',
    'B-52H': 'Planes',
    'BMD-1': 'Armed vehicles',
    'BMP-1': 'Armed vehicles',
    'BMP-2': 'Armed vehicles',
    'BMP-3': 'Armed vehicles',
    'BOMAN': 'Armed vehicles',
    'BRDM-2': 'Armed vehicles',
    'BRDM-2_malyutka': 'Armed vehicles',
    'BTR-60': 'Armed vehicles',
    'BTR-70': 'Armed vehicles',
    'BTR-80': 'Armed vehicles',
    'BTR-82A': 'Armed vehicles',
    'BTR-RD': 'Armed vehicles',
    'BTR_D': 'Armed vehicles',
    'Bf-109K-4': 'Planes',
    'Boman': 'Armed vehicles',
    'C-101CC': 'Planes',
    'C-101EB': 'Planes',
    'C-130': 'Planes',
    'C-130J-30': 'Planes',
    'C-17A': 'Planes',
    'C-47': 'Planes',
    'CH-47D': 'Helicopters',
    'CH-47Fbl1': 'Helicopters',
    'CH-53E': 'Helicopters',
    'CHAP_9K720_Cluster': 'Artillery',
    'CHAP_9K720_HE': 'Artillery',
    'CHAP_BMPT': 'Armed vehicles',
    'CHAP_FV101': 'Tanks',
    'CHAP_FV107': 'Armed vehicles',
    'CHAP_IRISTSLM_CP': 'Air Defence',
    'CHAP_IRISTSLM_LN': 'Air Defence',
    'CHAP_IRISTSLM_STR': 'Air Defence',
    'CHAP_M1130': 'Armed vehicles',
    'CHAP_M142_ATACMS_M39A1': 'Artillery',
    'CHAP_M142_ATACMS_M48': 'Artillery',
    'CHAP_M142_GMLRS_M30': 'Artillery',
    'CHAP_M142_GMLRS_M31': 'Artillery',
    'CHAP_MATV': 'Armed vehicles',
    'CHAP_PantsirS1': 'Air Defence',
    'CHAP_T64BV': 'Tanks',
    'CHAP_T84OplotM': 'Tanks',
    'CHAP_T90M': 'Tanks',
    'CHAP_TOS1A': 'Artillery',
    'CHAP_TorM2': 'Air Defence',
    'Centaur_IV': 'Tanks',
    'Challenger2': 'Tanks',
    'Chieftain_mk3': 'Tanks',
    'Christen Eagle II': 'Planes',
    'Churchill_VII': 'Tanks',
    'Cobra': 'Armed vehicles',
    'Cromwell_IV': 'Tanks',
    'Daimler_AC': 'Armed vehicles',
    'Dog Ear radar': 'Air Defence',
    'E-2C': 'Planes',
    'E-3A': 'Planes',
    'EWR 1L13': 'Air Defence',
    'EWR 55G6': 'Air Defence',
    'Elefant_SdKfz_184': 'Tanks',
    'F-100D': 'Planes',
    'F-117A': 'Planes',
    'F-14A': 'Planes',
    'F-14A-135-GR': 'Planes',
    'F-14A-135-GR-Early': 'Planes',
    'F-14A-95-GR': 'Planes',
    'F-14B': 'Planes',
    'F-14BU': 'Planes',
    'F-15C': 'Planes',
    'F-15E': 'Planes',
    'F-15ESE': 'Planes',
    'F-16A': 'Planes',
    'F-16A MLU': 'Planes',
    'F-16C bl.50': 'Planes',
    'F-16C bl.52d': 'Planes',
    'F-16C_50': 'Planes',
    'F-4E': 'Planes',
    'F-4E-45MC': 'Planes',
    'F-5E': 'Planes',
    'F-5E-3': 'Planes',
    'F-5E-3_FC': 'Planes',
    'F-86F Sabre': 'Planes',
    'F-86F_FC': 'Planes',
    'F/A-18A': 'Planes',
    'F/A-18C': 'Planes',
    'F4U-1D': 'Planes',
    'F4U-1D_CW': 'Planes',
    'FA-18C_hornet': 'Planes',
    'FPS-117': 'Air Defence',
    'FPS-117 Dome': 'Air Defence',
    'FPS-117 ECS': 'Air Defence',
    'FW-190A8': 'Planes',
    'FW-190D9': 'Planes',
    'Falcon_Gyrocopter': 'Planes',
    'Flakscheinwerfer_37': 'Air Defence',
    'FuMG-401': 'Air Defence',
    'FuSe-65': 'Air Defence',
    'Gepard': 'Air Defence',
    'Grad-URAL': 'Artillery',
    'Grad_FDDM': 'Armed vehicles',
    'H-6J': 'Planes',
    'HEMTT_C-RAM_Phalanx': 'Air Defence',
    'HL_B8M1': 'Artillery',
    'HL_DSHK': 'Armed vehicles',
    'HL_KORD': 'Armed vehicles',
    'HL_ZU-23': 'Air Defence',
    'HQ-7_LN_P': 'Air Defence',
    'HQ-7_LN_SP': 'Air Defence',
    'HQ-7_STR_SP': 'Air Defence',
    'Hawk': 'Planes',
    'Hawk AN/MPQ-46 TR': 'Air Defence',
    'Hawk AN/MPQ-50 SR': 'Air Defence',
    'Hawk M192 LN': 'Air Defence',
    'Hawk cwar': 'Air Defence',
    'Hawk ln': 'Air Defence',
    'Hawk pcp': 'Air Defence',
    'Hawk sr': 'Air Defence',
    'Hawk tr': 'Air Defence',
    'Hummer': 'Armed vehicles',
    'I-16': 'Planes',
    'IL-76MD': 'Planes',
    'IL-78M': 'Planes',
    'Igla manpad INS': 'Air Defence',
    'Infantry AK': 'Infantry',
    'Infantry AK Ins': 'Infantry',
    'Infantry AK ver2': 'Infantry',
    'Infantry AK ver3': 'Infantry',
    'J-11A': 'Planes',
    'JF-17': 'Planes',
    'JTAC': 'Infantry',
    'JagdPz_IV': 'Tanks',
    'Jagdpanther_G1': 'Tanks',
    'Ju-88A4': 'Planes',
    'KC-135': 'Planes',
    'KC130': 'Planes',
    'KC135MPRS': 'Planes',
    'KDO_Mod40': 'Air Defence',
    'KJ-2000': 'Planes',
    'KS-19': 'Air Defence',
    'Ka-27': 'Helicopters',
    'Ka-50': 'Helicopters',
    'Ka-50_3': 'Helicopters',
    'Kub 1S91 str': 'Air Defence',
    'Kub 2P25 ln': 'Air Defence',
    'L-39C': 'Planes',
    'L-39ZA': 'Planes',
    'L118_Unit': 'Artillery',
    'LARC-V': 'Armed vehicles',
    'LAV-25': 'Armed vehicles',
    'LEO1A3': 'Tanks',
    'LeFH_18-40-105': 'Artillery',
    'Leclerc': 'Tanks',
    'Leopard-2': 'Tanks',
    'Leopard-2A5': 'Tanks',
    'Leopard1A3': 'Tanks',
    'M-1 Abrams': 'Tanks',
    'M-109': 'Artillery',
    'M-113': 'Armed vehicles',
    'M-2 Bradley': 'Armed vehicles',
    'M-2000C': 'Planes',
    'M-60': 'Tanks',
    'M1025 HMMWV': 'Armed vehicles',
    'M1043 HMMWV Armament': 'Armed vehicles',
    'M1045 HMMWV TOW': 'Armed vehicles',
    'M109': 'Artillery',
    'M1097 Avenger': 'Air Defence',
    'M10_GMC': 'Tanks',
    'M1126 Stryker ICV': 'Armed vehicles',
    'M1128 Stryker MGS': 'Tanks',
    'M113': 'Armed vehicles',
    'M1134 Stryker ATGM': 'Armed vehicles',
    'M12_GMC': 'Artillery',
    'M163 Vulcan': 'Air Defence',
    'M1A2 Abrams': 'Tanks',
    'M1A2C_SEP_V3': 'Tanks',
    'M1_37mm': 'Air Defence',
    'M270 MLRS': 'Artillery',
    'M2A1-105': 'Artillery',
    'M2A1_halftrack': 'Armed vehicles',
    'M2A2 Bradley': 'Armed vehicles',
    'M30_CC': 'Armed vehicles',
    'M45_Quadmount': 'Air Defence',
    'M48 Chaparral': 'Air Defence',
    'M4A4_Sherman_FF': 'Tanks',
    'M4_Sherman': 'Tanks',
    'M4_Tractor': 'Armed vehicles',
    'M6 Linebacker': 'Air Defence',
    'M60A3': 'Tanks',
    'M8_Greyhound': 'Armed vehicles',
    'MB-339A': 'Planes',
    'MB-339APAN': 'Planes',
    'MCV-80': 'Armed vehicles',
    'MLRS': 'Artillery',
    'MLRS BM-21 Grad': 'Artillery',
    'MLRS FDDM': 'Armed vehicles',
    'MLRS Smerch 9A52': 'Artillery',
    'MQ-9 Reaper': 'Planes',
    'MTLB': 'Armed vehicles',
    'Marder': 'Armed vehicles',
    'Maschinensatz_33': 'Air Defence',
    'MaxxPro_MRAP': 'Armed vehicles',
    'Merkava_Mk4': 'Tanks',
    'Mi-24P': 'Planes',
    'Mi-24V': 'Helicopters',
    'Mi-26': 'Planes',
    'Mi-28N': 'Helicopters',
    'Mi-8MT': 'Planes',
    'MiG-15bis': 'Planes',
    'MiG-15bis_FC': 'Planes',
    'MiG-19P': 'Planes',
    'MiG-21Bis': 'Planes',
    'MiG-23MLD': 'Planes',
    'MiG-25PD': 'Planes',
    'MiG-25RBT': 'Planes',
    'MiG-27K': 'Planes',
    'MiG-29 Fulcrum': 'Planes',
    'MiG-29A': 'Planes',
    'MiG-29G': 'Planes',
    'MiG-29S': 'Planes',
    'MiG-31': 'Planes',
    'Mirage 2000-5': 'Planes',
    'Mirage-F1AD': 'Planes',
    'Mirage-F1AZ': 'Planes',
    'Mirage-F1B': 'Planes',
    'Mirage-F1BD': 'Planes',
    'Mirage-F1BE': 'Planes',
    'Mirage-F1BQ': 'Planes',
    'Mirage-F1C': 'Planes',
    'Mirage-F1C-200': 'Planes',
    'Mirage-F1CE': 'Planes',
    'Mirage-F1CG': 'Planes',
    'Mirage-F1CH': 'Planes',
    'Mirage-F1CJ': 'Planes',
    'Mirage-F1CK': 'Planes',
    'Mirage-F1CR': 'Planes',
    'Mirage-F1CT': 'Planes',
    'Mirage-F1CZ': 'Planes',
    'Mirage-F1DDA': 'Planes',
    'Mirage-F1ED': 'Planes',
    'Mirage-F1EDA': 'Planes',
    'Mirage-F1EE': 'Planes',
    'Mirage-F1EH': 'Planes',
    'Mirage-F1EQ': 'Planes',
    'Mirage-F1JA': 'Planes',
    'Mirage-F1M-CE': 'Planes',
    'Mirage-F1M-EE': 'Planes',
    'MosquitoFBMkVI': 'Planes',
    'NASAMS_Command_Post': 'Air Defence',
    'NASAMS_LN_B': 'Air Defence',
    'NASAMS_LN_C': 'Air Defence',
    'NASAMS_Radar_MPQ64F1': 'Air Defence',
    'OH-58D': 'Helicopters',
    'OH58D': 'Helicopters',
    'Osa 9A33 ln': 'Air Defence',
    'P-47D-30': 'Planes',
    'P-47D-30bl1': 'Planes',
    'P-47D-40': 'Planes',
    'P-51D': 'Planes',
    'P-51D-30-NA': 'Planes',
    'P14_SR': 'Air Defence',
    'PLZ05': 'Artillery',
    'PT_76': 'Tanks',
    'Pak40': 'Artillery',
    'Paratrooper AKS-74': 'Infantry',
    'Paratrooper RPG-16': 'Infantry',
    'Patriot AMG': 'Air Defence',
    'Patriot ECS': 'Air Defence',
    'Patriot EPP': 'Air Defence',
    'Patriot cp': 'Air Defence',
    'Patriot ln': 'Air Defence',
    'Patriot str': 'Air Defence',
    'Pz_IV_H': 'Tanks',
    'Pz_V_Panther_G': 'Tanks',
    'QF-4E': 'Planes',
    'QF_37_AA': 'Air Defence',
    'RD_75': 'Air Defence',
    'RLS_19J6': 'Air Defence',
    'RPC_5N62V': 'Air Defence',
    'RQ-1A Predator': 'Planes',
    'Roland ADS': 'Air Defence',
    'Roland Radar': 'Air Defence',
    'Roland rdr': 'Air Defence',
    'S-200_Launcher': 'Air Defence',
    'S-300PS 40B6M tr': 'Air Defence',
    'S-300PS 40B6MD sr': 'Air Defence',
    'S-300PS 40B6MD sr_19J6': 'Air Defence',
    'S-300PS 54K6 cp': 'Air Defence',
    'S-300PS 5H63C 30H6_tr': 'Air Defence',
    'S-300PS 5P85C ln': 'Air Defence',
    'S-300PS 5P85D ln': 'Air Defence',
    'S-300PS 64H6E sr': 'Air Defence',
    'S-3B': 'Planes',
    'S-3B Tanker': 'Planes',
    'S-60_Type59_Artillery': 'Air Defence',
    'SA-11 Buk CC 9S470M1': 'Air Defence',
    'SA-11 Buk LN 9A310M1': 'Air Defence',
    'SA-11 Buk SR 9S18M1': 'Air Defence',
    'SA-13 Strela-10M3 9A35M3': 'Air Defence',
    'SA-15 Tor 9A331': 'Air Defence',
    'SA-18 Igla comm': 'Air Defence',
    'SA-18 Igla manpad': 'Air Defence',
    'SA-18 Igla-S comm': 'Air Defence',
    'SA-18 Igla-S manpad': 'Air Defence',
    'SA-19 Tunguska 2S6': 'Air Defence',
    'SA-6 Kub LN 2P25': 'Air Defence',
    'SA-6 Kub STR 9S91': 'Air Defence',
    'SA-8 Osa 9A33': 'Air Defence',
    'SA-9 Strela-1 9P31': 'Air Defence',
    'SA342L': 'Helicopters',
    'SA342M': 'Helicopters',
    'SA342Minigun': 'Helicopters',
    'SA342Mistral': 'Helicopters',
    'SAU 2-C9': 'Artillery',
    'SAU Akatsia': 'Artillery',
    'SAU Gvozdika': 'Artillery',
    'SAU Msta': 'Artillery',
    'SH-3W': 'Helicopters',
    'SH-60B': 'Helicopters',
    'SK_C_28_naval_gun': 'Artillery',
    'SNR_75V': 'Air Defence',
    'SON_9': 'Air Defence',
    'SR 9S80 Ovod-M-SV': 'Air Defence',
    'S_75M_Volhov': 'Air Defence',
    'Scud_B': 'Artillery',
    'Sd_Kfz_2': 'Armed vehicles',
    'Sd_Kfz_234_2_Puma': 'Armed vehicles',
    'Sd_Kfz_251': 'Armed vehicles',
    'Sd_Kfz_7': 'Armed vehicles',
    'Silkworm_SR': 'Artillery',
    'Smerch': 'Artillery',
    'Smerch_HE': 'Artillery',
    'Soldier AK': 'Infantry',
    'Soldier M249': 'Infantry',
    'Soldier M4': 'Infantry',
    'Soldier M4 GRG': 'Infantry',
    'Soldier RPG': 'Infantry',
    'Soldier stinger': 'Air Defence',
    'SpGH_Dana': 'Artillery',
    'SpitfireLFMkIX': 'Planes',
    'SpitfireLFMkIXCW': 'Planes',
    'Stinger comm': 'Air Defence',
    'Stinger comm dsr': 'Air Defence',
    'Stinger manpad': 'Air Defence',
    'Stinger manpad GRG': 'Air Defence',
    'Stinger manpad dsr': 'Air Defence',
    'Strela-1 9P31': 'Air Defence',
    'Strela-10M3': 'Air Defence',
    'Stug_III': 'Tanks',
    'Stug_IV': 'Tanks',
    'SturmPzIV': 'Artillery',
    'Su-17M4': 'Planes',
    'Su-24M': 'Planes',
    'Su-24MR': 'Planes',
    'Su-25': 'Planes',
    'Su-25T': 'Planes',
    'Su-25TM': 'Planes',
    'Su-27': 'Planes',
    'Su-30': 'Planes',
    'Su-33': 'Planes',
    'Su-34': 'Planes',
    'T-34-85': 'Tanks',
    'T-55': 'Tanks',
    'T-72B': 'Tanks',
    'T-72B3': 'Tanks',
    'T-80B': 'Tanks',
    'T-80U': 'Tanks',
    'T-80UD': 'Tanks',
    'T-90': 'Tanks',
    'T155_Firtina': 'Artillery',
    'T62M': 'Tanks',
    'TF-51D': 'Planes',
    'TPZ': 'Armed vehicles',
    'TYPE-59': 'Tanks',
    'Tetrarch': 'Armed vehicles',
    'Tiger_I': 'Tanks',
    'Tiger_II_H': 'Tanks',
    'Tigr_233036': 'Armed vehicles',
    'Tor 9A331': 'Air Defence',
    'Tornado GR3': 'Planes',
    'Tornado GR4': 'Planes',
    'Tornado IDS': 'Planes',
    'Tu-142': 'Planes',
    'Tu-160': 'Planes',
    'Tu-22M3': 'Planes',
    'Tu-95MS': 'Planes',
    'Type_3_80mm_AA': 'Air Defence',
    'Type_88_75mm_AA': 'Air Defence',
    'Type_89_I_Go': 'Tanks',
    'Type_94_25mm_AA_Truck': 'Air Defence',
    'Type_96_25mm_AA': 'Air Defence',
    'Type_98_Ke_Ni': 'Tanks',
    'Type_98_So_Da': 'Armed vehicles',
    'UH-1H': 'Planes',
    'UH-60A': 'Helicopters',
    'Uragan_BM-27': 'Artillery',
    'Ural-375 ZU-23': 'Air Defence',
    'Ural-375 ZU-23 Insurgent': 'Air Defence',
    'VAB_Mephisto': 'Armed vehicles',
    'Vulcan': 'Air Defence',
    'Wespe124': 'Artillery',
    'WingLoong-I': 'Planes',
    'Yak-40': 'Planes',
    'Yak-52': 'Planes',
    'ZBD04A': 'Armed vehicles',
    'ZSU-23-4 Shilka': 'Air Defence',
    'ZSU_57_2': 'Air Defence',
    'ZTZ96B': 'Tanks',
    'ZU-23 Closed Insurgent': 'Air Defence',
    'ZU-23 Emplacement': 'Air Defence',
    'ZU-23 Emplacement Closed': 'Air Defence',
    'ZU-23 Insurgent': 'Air Defence',
    'bofors40': 'Air Defence',
    'flak18': 'Air Defence',
    'flak30': 'Air Defence',
    'flak36': 'Air Defence',
    'flak37': 'Air Defence',
    'flak38': 'Air Defence',
    'flak41': 'Air Defence',
    'generator_5i57': 'Air Defence',
    'hy_launcher': 'Artillery',
    'leopard-2A4': 'Tanks',
    'leopard-2A4_trs': 'Tanks',
    'p-19 s-125 sr': 'Air Defence',
    'rapier_fsa_blindfire_radar': 'Air Defence',
    'rapier_fsa_launcher': 'Air Defence',
    'rapier_fsa_optical_tracker_unit': 'Air Defence',
    'snr s-125 tr': 'Air Defence',
    'soldier_mauser98': 'Infantry',
    'soldier_wwii_br_01': 'Infantry',
    'soldier_wwii_us': 'Infantry',
    'tacr2a': 'Armed vehicles',
    'tt_B8M1': 'Artillery',
    'tt_DSHK': 'Armed vehicles',
    'tt_KORD': 'Armed vehicles',
    'tt_ZU-23': 'Air Defence',
    'v1_launcher': 'Artillery',
}

# --- API publique -------------------------------------------------------------


def categorie(cle: str) -> str:
    """Catégorie de regroupement pour `cle`, utilisée par `_group_salves`
    (brief §5). Celle de `_LEXIQUE` prime si posée ; sinon celle de
    `_CATEGORIE_PAR_CLE` ; **sinon `cle` elle-même** -- jamais `None`. Ce
    repli sur la clé garantit qu'une salve ne regroupe jamais par erreur
    deux types que le lexique ignore l'un et l'autre : deux clés inconnues
    distinctes restent deux catégories distinctes (chacune sa propre clé),
    exactement le comportement d'avant ce lot pour les clés hors lexique."""
    if cle in _LEXIQUE:
        return _LEXIQUE[cle][1]
    return _CATEGORIE_PAR_CLE.get(cle, cle)


def resoudre(cle: str | None) -> str | None:
    """Libellé lisible pour `cle`, trois niveaux de repli (brief §4).
    `None` si `cle` est `None` (aucune clé à résoudre) -- jamais une valeur
    inventée."""
    if cle is None:
        return None
    if cle in _LEXIQUE:
        return _LEXIQUE[cle][0]
    cat = _CATEGORIE_PAR_CLE.get(cle)
    if cat is not None:
        return _CATEGORIES_GENERIQUES[cat]
    return cle


# --- Table d'équivalence des noms d'arme (brief Lot Fusion §2, geste 1) ------
# Deux clients DCS peuvent nommer différemment la MÊME munition -- fait
# mesuré sur la session du 14 septembre : deux Mi-24P emportant 10 roquettes
# chacun en annoncent 20, faute de fusion (`S-13OF Blast/Fragmentation` /
# `S-13OF Explosion/fragmentation`, deux noms pour une seule munition).
# Table explicite uniquement : les armes inventoriées sur les deux sessions
# disponibles (`SNEB Type 256 F1B HE/Frag`, `BLG-66 Belouga AC`, `9M114
# Shturm (AT-6 Spiral)`, `Mk-20 Rockeye`, `GBU-8/B`) montrent des variantes
# réellement distinctes (SNEB Type 251 / 256 / 257) -- une règle de
# troncature automatique les fusionnerait à tort. Ne contient que les
# variantes mesurées ; `S-8KOM HEAT/Frag` n'a montré aucune divergence, il
# n'entre pas.
_ALIAS_ARME: dict[str, str] = {
    "S-13OF Blast/Fragmentation": "S-13OF",
    "S-13OF Explosion/fragmentation": "S-13OF",
    # Lot « Polish du moteur du Débrief » (v1.0039) : seize munitions d'unités
    # au sol que deux clients DCS écrivent de deux façons, mesurées sur les
    # journaux de production du 9 octobre 2026. Le nom canonique est toujours
    # une clé que le référentiel de production nomme déjà.
    "L23_120_AP": "L23 (120mm APFSDS-T)",
    "2A64_152": "3OF45 (152mm HE)",
    "UOF412_100HE": "UOF412 (100mm HE)",
    "L31_120mm_HESH": "L31 (120mm HESH)",
    "SMERCH HE": "9M55F (300mm HE)",
    "M256_120_HE": "M830 (120mm HEAT-MP-T)",
    "SMERCH": "9M55K (300mm CM-AP)",
    "57mm HE-T": "UOR-281 (57mm HE-T)",
    "9M31 Strela-1": "9M31 Strela-1 (SA-9 Gaskin)",
    "3UBM11_100mm_AP": "3UBM11 (100mm APFSDS-T)",
    "DM12_L55_120mm_HEAT_MP_T": "DM12 (120mm HEAT-MP-T)",
    "9M333 Strela-10": "9M333 Strela-10 (SA-13 Gopher)",
    "DM12_120mm_HEAT_MP_T": "DM12 (120mm HEAT-MP-T)",
    "DM53_120_AP": "DM53 (120mm APFSDS-T)",
    "3M9M Kub": "3M9M Kub (SA-6 Gainful)",
    "5V27 S-125": "5V27 S-125 Neva (SA-3 Goa)",
}


def canon_arme(nom: str | None) -> str | None:
    """Ramène un nom d'arme divergent à sa désignation canonique.

    1. `None` ou chaîne vide -> `None`, inchangé.
    2. Correspondance exacte dans `_ALIAS_ARME` -> la valeur canonique.
    3. Sinon, la chaîne telle quelle. Jamais de découpage, jamais de
       devinette (brief §2, geste 1)."""
    if not nom:
        return None
    return _ALIAS_ARME.get(nom, nom)
