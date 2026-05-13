import json

with open('frontend/matches.json', encoding='utf-8') as f:
    data = json.load(f)
    
matches = data['matches']
valid_totals = [m for m in matches if m.get('total_over') != '0.00' and m.get('total_value')]
valid_handicaps = [m for m in matches if m.get('handicap_1') != '0.00' and m.get('handicap_1_value')]

print(f"Total Matches: {len(matches)}")
print(f"Matches with valid Totals: {len(valid_totals)}")
print(f"Matches with valid Handicaps: {len(valid_handicaps)}")

if valid_totals:
    print("\n--- Example Match with Total ---")
    m = valid_totals[0]
    print(f"{m['team1']} vs {m['team2']}")
    print(f"Total Value: {m['total_value']}")
    print(f"Over: {m['total_over']}, Under: {m['total_under']}")

if valid_handicaps:
    print("\n--- Example Match with Handicap ---")
    m = valid_handicaps[0]
    print(f"{m['team1']} vs {m['team2']}")
    print(f"Handicap 1 Value: {m['handicap_1_value']} (Odds: {m['handicap_1']})")
    print(f"Handicap 2 Value: {m['handicap_2_value']} (Odds: {m['handicap_2']})")
