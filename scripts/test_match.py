import difflib

def _normalize(name: str) -> str:
    if not name: return ""
    s = name.lower()
    words = s.split()
    words = [w for w in words if w not in ("fc", "fk", "jk", "sc", "cs", "club", "team", "the", "al", "afc", "cfc", "cd", "ac", "rc", "ud")]
    return " ".join(words).replace("-", " ").strip()

def _teams_match(our_t1: str, our_t2: str, api_t1: str, api_t2: str) -> bool:
    a1 = _normalize(our_t1)
    a2 = _normalize(our_t2)
    b1 = _normalize(api_t1)
    b2 = _normalize(api_t2)
    
    def core_match(name1, name2):
        if not name1 or not name2: return False
        
        # Age group
        def get_age_group(n):
            for w in n.split():
                if w.startswith("u") and w[1:].isdigit():
                    return w
            return None
        age1 = get_age_group(name1)
        age2 = get_age_group(name2)
        if age1 and age2 and age1 != age2: return False
        if bool(age1) != bool(age2): return False
            
        # Women
        def has_women(n):
            return "women" in n.split() or " (w) " in f" {n} " or "(w)" in n.replace(" ", "") or " w " in f" {n} "
        if has_women(name1) != has_women(name2): return False
            
        ratio = difflib.SequenceMatcher(None, name1, name2).ratio()
        if ratio > 0.88: return True
            
        set1 = set(name1.split())
        set2 = set(name2.split())
        if not set1 or not set2: return False
        
        intersect = set1 & set2
        
        # Remove generic tokens from intersection to see if they share any REAL words
        meaningful_intersect = {w for w in intersect if len(w) > 2 and not (w.startswith("u") and w[1:].isdigit()) and w not in {"united", "city", "real", "athletic", "sporting", "dynamo", "boys", "girls", "women", "men"}}
        
        if meaningful_intersect:
            if ("united" in set1 ^ set2) and ("city" in set1 ^ set2): return False
            if ("real" in set1 ^ set2) and ("atletico" in set1 ^ set2): return False
            if ("inter" in set1 ^ set2) and ("ac" in set1 ^ set2): return False
            if ("aston" in set1 ^ set2) and ("west" in set1 ^ set2): return False
            
            return True
                
        # Subset fallback
        if set1.issubset(set2) or set2.issubset(set1):
            longest_word = max(set1 | set2, key=len)
            if len(longest_word) > 4:
                only_share_generic = not meaningful_intersect
                if not only_share_generic:
                    return True
            
        return False

    def pair_match(p1a, p1b, p2a, p2b):
        return core_match(p1a, p2a) and core_match(p1b, p2b)

    return pair_match(a1, a2, b1, b2) or pair_match(a1, a2, b2, b1)

tests = [
    ("Leeds United", "Sunderland AFC", "Leeds U21", "Sunderland U21"),
    ("Genoa CFC U20", "Hellas Verona U20", "Genoa U20", "Hellas Verona U20"),
    ("Manchester City", "Arsenal", "Manchester United", "Arsenal"),
    ("Real Madrid", "Getafe", "Real Sociedad", "Getafe"),
    ("Gil Vicente", "Benfica", "Gil Vicente", "Benfica"),
    ("France W U19", "Italy U19 W", "Portugal U19 W", "Czech Republic U19 W"),
    ("Inter Milan", "Juventus", "AC Milan", "Juventus"),
    ("Leeds United", "Sunderland AFC", "Leeds", "Sunderland")
]

for t1, t2, a1, a2 in tests:
    print(f"{t1} vs {t2}  <=>  {a1} vs {a2} : {_teams_match(t1,t2,a1,a2)}")
