import server

test_chords = [
    "C", "Cm", "Cdim", "Caug", "Csus2", "Csus4", "C6", "Cm6",
    "C7", "Cmaj7", "Cm7", "Cdim7", "Cm7b5", "CmMaj7",
    "C9", "Cmaj9", "Cm9", "C11", "C13", "Cadd9", "C6/9",
    "C7b5", "C7#5", "C7b9", "C7#9", "C/E", "Am7", "F#m7b5"
]

print(f"{'Chord':<10} | {'Notes':<20} | {'Quality'}")
print("-" * 55)
for ch in test_chords:
    res = server.get_chord(ch)
    if "error" in res:
        print(f"{ch:<10} | ERROR: {res['error']}")
    else:
        print(f"{ch:<10} | {res['notes_str']:<20} | {res['quality']}")
