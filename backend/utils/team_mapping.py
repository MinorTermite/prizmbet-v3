# -*- coding: utf-8 -*-
"""Team name normalization utilities"""

TEAM_ALIASES = {
    # English Premier League
    "manchester united": "Manchester United",
    "man united": "Manchester United",
    "man utd": "Manchester United",
    "манчестер юнайтед": "Manchester United",
    "манчестер юн": "Manchester United",
    "ман юнайтед": "Manchester United",

    "arsenal": "Arsenal",
    "арсенал": "Arsenal",
    "арсенал лондон": "Arsenal",

    "liverpool": "Liverpool",
    "ливерпуль": "Liverpool",

    "chelsea": "Chelsea",
    "челси": "Chelsea",

    "manchester city": "Manchester City",
    "man city": "Manchester City",
    "манчестер сити": "Manchester City",
    "ман сити": "Manchester City",

    "tottenham hotspur": "Tottenham",
    "tottenham": "Tottenham",
    "тоттенхэм": "Tottenham",
    "тоттенхем": "Tottenham",

    # La Liga
    "real madrid": "Real Madrid",
    "реал мадрид": "Real Madrid",

    "fc barcelona": "Barcelona",
    "barcelona": "Barcelona",
    "барселона": "Barcelona",
    "барса": "Barcelona",

    "atletico madrid": "Atletico Madrid",
    "атлетико мадрид": "Atletico Madrid",
    "атлетико": "Atletico Madrid",

    # Serie A
    "juventus": "Juventus",
    "ювентус": "Juventus",

    "inter milan": "Inter Milan",
    "internazionale": "Inter Milan",
    "интер": "Inter Milan",
    "интер милан": "Inter Milan",

    "ac milan": "AC Milan",
    "milan": "AC Milan",
    "милан": "AC Milan",

    "ssc napoli": "Napoli",
    "napoli": "Napoli",
    "наполи": "Napoli",

    # Bundesliga
    "bayern munich": "Bayern Munich",
    "fc bayern münchen": "Bayern Munich",
    "fc bayern munich": "Bayern Munich",
    "бавария": "Bayern Munich",
    "бавария мюнхен": "Bayern Munich",

    "borussia dortmund": "Borussia Dortmund",
    "bvb": "Borussia Dortmund",
    "дортмунд": "Borussia Dortmund",
    "боруссия дортмунд": "Borussia Dortmund",

    # Ligue 1
    "paris saint-germain": "PSG",
    "paris saint germain": "PSG",
    "psg": "PSG",
    "пари сен-жермен": "PSG",
    "псж": "PSG",

    # RPL (Российская Премьер-Лига)
    "зенит": "Zenit",
    "zenit": "Zenit",
    "зенит санкт-петербург": "Zenit",

    "спартак москва": "Spartak Moscow",
    "спартак": "Spartak Moscow",
    "spartak moscow": "Spartak Moscow",

    "цска москва": "CSKA Moscow",
    "цска": "CSKA Moscow",
    "cska moscow": "CSKA Moscow",

    "локомотив москва": "Lokomotiv Moscow",
    "локомотив": "Lokomotiv Moscow",
    "lokomotiv moscow": "Lokomotiv Moscow",

    "динамо москва": "Dynamo Moscow",
    "dynamo moscow": "Dynamo Moscow",

    "краснодар": "Krasnodar",
    "fk krasnodar": "Krasnodar",
    "krasnodar": "Krasnodar",

    # Add more as needed...
}


class TeamNormalizer:
    """Normalizes team names to canonical form using alias mapping."""

    def __init__(self):
        self.aliases = TEAM_ALIASES

    def normalize(self, name: str) -> str:
        """Return canonical team name, or original if not found."""
        if not name:
            return name
        key = name.strip().lower()
        return self.aliases.get(key, name)


team_normalizer = TeamNormalizer()
