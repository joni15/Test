from .migros import MigrosScraper
from .coop import CoopScraper
from .denner import DennerScraper
from .lidl import LidlScraper
from .aldi import AldiScraper

ALL_SCRAPERS = [MigrosScraper, CoopScraper, DennerScraper, LidlScraper, AldiScraper]
