"""Riot API constants and enum definitions."""

from enum import Enum


class Region(str, Enum):
    """Riot API regions for regional routing."""

    AMERICAS = "americas"
    ASIA = "asia"
    EUROPE = "europe"
    SEA = "sea"


class Platform(str, Enum):
    """Riot API platforms for platform routing."""

    BR1 = "br1"
    EUN1 = "eun1"
    EUW1 = "euw1"
    JP1 = "jp1"
    KR = "kr"
    LA1 = "la1"
    LA2 = "la2"
    NA1 = "na1"
    OC1 = "oc1"
    PH2 = "ph2"
    RU = "ru"
    SG2 = "sg2"
    TH2 = "th2"
    TR1 = "tr1"
    TW2 = "tw2"
    VN2 = "vn2"


class QueueType(int, Enum):
    """Riot API queue types for match filtering."""

    # Ranked queues
    RANKED_SOLO_5X5 = 420
    RANKED_FLEX_5X5 = 440
    RANKED_FLEX_3X3 = 470

    # Normal queues
    NORMAL_DRAFT_5X5 = 400
    NORMAL_BLIND_PICK_5X5 = 430
    NORMAL_BLIND_PICK_3X3 = 450
    ARAM = 450

    # Other queues
    PRACTICE_TOOL = 2000
    TUTORIAL_1 = 2010
    TUTORIAL_2 = 2011
    TUTORIAL_3 = 2012

    # Event/Rotation queues
    ASSASSINATE = 600
    ONE_FOR_ALL = 610
    HEXAKILL = 620
    URF = 630
    DOOM_BOTS = 640
    ASCENSION = 650
    PoroKing = 700
    NEXUS_SIEGE = 720
    DefinitelyNotDominion = 800
    ARURF = 830
    PROJECT = 840
    OVERCHARGE = 860
    SNOWURF = 870
    Odyssey = 880
