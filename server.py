"""Piano Music MCP Server - Music Intelligence Layer.

This server exposes Model Context Protocol (MCP) tools to analyze chords,
explore musical scales, and transpose chords using algorithmic music theory.
"""

from __future__ import annotations

import json
import re
from typing import Any
from mcp.server import MCPServer

# ==============================================================================
# 1. MUSIC THEORY ENGINE (Separated from MCP logic)
# ==============================================================================

DIATONIC_LETTERS = ["C", "D", "E", "F", "G", "A", "B"]
NATURAL_SEMITONES: dict[str, int] = {
    "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11
}

NOTE_TO_SEMITONE: dict[str, int] = {
    "C": 0, "B#": 0,
    "C#": 1, "DB": 1,
    "D": 2,
    "D#": 3, "EB": 3,
    "E": 4, "FB": 4,
    "E#": 5, "F": 5,
    "F#": 6, "GB": 6,
    "G": 7,
    "G#": 8, "AB": 8,
    "A": 9,
    "A#": 10, "BB": 10,
    "B": 11, "CB": 11,
}

INTERVAL_DEGREE_MAP: dict[str, int] = {
    "1": 1,
    "b2": 2, "2": 2, "#2": 2,
    "b3": 3, "3": 3, "#3": 3,
    "4": 4, "#4": 4, "b5": 5, "5": 5, "#5": 5,
    "6": 6, "b6": 6, "bb7": 7, "b7": 7, "7": 7,
    "b9": 2, "9": 2, "#9": 2,
    "11": 4, "#11": 4,
    "b13": 6, "13": 6,
}

# Formula definitions: (Display Name, Semitone offsets from root, Interval names)
CHORD_FORMULAS: dict[str, tuple[str, list[int], list[str]]] = {
    # Triads
    "": ("Major", [0, 4, 7], ["1", "3", "5"]),
    "MAJ": ("Major", [0, 4, 7], ["1", "3", "5"]),
    "MAJOR": ("Major", [0, 4, 7], ["1", "3", "5"]),
    "M": ("Minor", [0, 3, 7], ["1", "b3", "5"]),
    "MIN": ("Minor", [0, 3, 7], ["1", "b3", "5"]),
    "MINOR": ("Minor", [0, 3, 7], ["1", "b3", "5"]),
    "-": ("Minor", [0, 3, 7], ["1", "b3", "5"]),
    "DIM": ("Diminished", [0, 3, 6], ["1", "b3", "b5"]),
    "AUG": ("Augmented", [0, 4, 8], ["1", "3", "#5"]),
    "+": ("Augmented", [0, 4, 8], ["1", "3", "#5"]),
    "SUS2": ("Suspended 2nd", [0, 2, 7], ["1", "2", "5"]),
    "SUS4": ("Suspended 4th", [0, 5, 7], ["1", "4", "5"]),
    "SUS": ("Suspended 4th", [0, 5, 7], ["1", "4", "5"]),

    # 6th chords
    "6": ("Major 6th", [0, 4, 7, 9], ["1", "3", "5", "6"]),
    "MAJ6": ("Major 6th", [0, 4, 7, 9], ["1", "3", "5", "6"]),
    "M6": ("Minor 6th", [0, 3, 7, 9], ["1", "b3", "5", "6"]),
    "MIN6": ("Minor 6th", [0, 3, 7, 9], ["1", "b3", "5", "6"]),
    "6/9": ("6/9", [0, 4, 7, 9, 2], ["1", "3", "5", "6", "9"]),
    "69": ("6/9", [0, 4, 7, 9, 2], ["1", "3", "5", "6", "9"]),

    # 7th chords
    "7": ("Dominant 7th", [0, 4, 7, 10], ["1", "3", "5", "b7"]),
    "DOM7": ("Dominant 7th", [0, 4, 7, 10], ["1", "3", "5", "b7"]),
    "MAJ7": ("Major 7th", [0, 4, 7, 11], ["1", "3", "5", "7"]),
    "M7": ("Minor 7th", [0, 3, 7, 10], ["1", "b3", "5", "b7"]),
    "MIN7": ("Minor 7th", [0, 3, 7, 10], ["1", "b3", "5", "b7"]),
    "-7": ("Minor 7th", [0, 3, 7, 10], ["1", "b3", "5", "b7"]),
    "DIM7": ("Diminished 7th", [0, 3, 6, 9], ["1", "b3", "b5", "bb7"]),
    "O7": ("Diminished 7th", [0, 3, 6, 9], ["1", "b3", "b5", "bb7"]),
    "O": ("Diminished 7th", [0, 3, 6, 9], ["1", "b3", "b5", "bb7"]),
    "M7B5": ("Half-Diminished 7th", [0, 3, 6, 10], ["1", "b3", "b5", "b7"]),
    "MIN7B5": ("Half-Diminished 7th", [0, 3, 6, 10], ["1", "b3", "b5", "b7"]),
    "HALF-DIM": ("Half-Diminished 7th", [0, 3, 6, 10], ["1", "b3", "b5", "b7"]),
    "Ø": ("Half-Diminished 7th", [0, 3, 6, 10], ["1", "b3", "b5", "b7"]),
    "MMAJ7": ("Minor-Major 7th", [0, 3, 7, 11], ["1", "b3", "5", "7"]),
    "MINMAJ7": ("Minor-Major 7th", [0, 3, 7, 11], ["1", "b3", "5", "7"]),

    # Extended 9ths
    "9": ("Dominant 9th", [0, 4, 7, 10, 2], ["1", "3", "5", "b7", "9"]),
    "MAJ9": ("Major 9th", [0, 4, 7, 11, 2], ["1", "3", "5", "7", "9"]),
    "M9": ("Minor 9th", [0, 3, 7, 10, 2], ["1", "b3", "5", "b7", "9"]),
    "MIN9": ("Minor 9th", [0, 3, 7, 10, 2], ["1", "b3", "5", "b7", "9"]),

    # Extended 11ths
    "11": ("Dominant 11th", [0, 4, 7, 10, 2, 5], ["1", "3", "5", "b7", "9", "11"]),
    "MAJ11": ("Major 11th", [0, 4, 7, 11, 2, 5], ["1", "3", "5", "7", "9", "11"]),
    "M11": ("Minor 11th", [0, 3, 7, 10, 2, 5], ["1", "b3", "5", "b7", "9", "11"]),
    "MIN11": ("Minor 11th", [0, 3, 7, 10, 2, 5], ["1", "b3", "5", "b7", "9", "11"]),

    # Extended 13ths
    "13": ("Dominant 13th", [0, 4, 7, 10, 2, 9], ["1", "3", "5", "b7", "9", "13"]),
    "MAJ13": ("Major 13th", [0, 4, 7, 11, 2, 9], ["1", "3", "5", "7", "9", "13"]),
    "M13": ("Minor 13th", [0, 3, 7, 10, 2, 9], ["1", "b3", "5", "b7", "9", "13"]),
    "MIN13": ("Minor 13th", [0, 3, 7, 10, 2, 9], ["1", "b3", "5", "b7", "9", "13"]),

    # Added tones
    "ADD9": ("Add 9", [0, 4, 7, 2], ["1", "3", "5", "9"]),
    "MADD9": ("Minor Add 9", [0, 3, 7, 2], ["1", "b3", "5", "9"]),
    "ADD11": ("Add 11", [0, 4, 7, 5], ["1", "3", "5", "11"]),
    "ADD13": ("Add 13", [0, 4, 7, 9], ["1", "3", "5", "13"]),

    # Altered dominant chords
    "7B5": ("Dominant 7th (b5)", [0, 4, 6, 10], ["1", "3", "b5", "b7"]),
    "7#5": ("Dominant 7th (#5)", [0, 4, 8, 10], ["1", "3", "#5", "b7"]),
    "7+5": ("Dominant 7th (#5)", [0, 4, 8, 10], ["1", "3", "#5", "b7"]),
    "7AUG": ("Dominant 7th Augmented", [0, 4, 8, 10], ["1", "3", "#5", "b7"]),
    "7B9": ("Dominant 7th (b9)", [0, 4, 7, 10, 1], ["1", "3", "5", "b7", "b9"]),
    "7#9": ("Dominant 7th (#9)", [0, 4, 7, 10, 3], ["1", "3", "5", "b7", "#9"]),
}

# Scale formulas: (Display Name, Semitone offsets from root, Degree labels)
SCALE_FORMULAS: dict[str, tuple[str, list[int], list[str]]] = {
    "MAJOR": ("Major (Ionian)", [0, 2, 4, 5, 7, 9, 11], ["1", "2", "3", "4", "5", "6", "7"]),
    "IONIAN": ("Major (Ionian)", [0, 2, 4, 5, 7, 9, 11], ["1", "2", "3", "4", "5", "6", "7"]),
    "NATURAL_MINOR": ("Natural Minor (Aeolian)", [0, 2, 3, 5, 7, 8, 10], ["1", "2", "b3", "4", "5", "b6", "b7"]),
    "MINOR": ("Natural Minor (Aeolian)", [0, 2, 3, 5, 7, 8, 10], ["1", "2", "b3", "4", "5", "b6", "b7"]),
    "AEOLIAN": ("Natural Minor (Aeolian)", [0, 2, 3, 5, 7, 8, 10], ["1", "2", "b3", "4", "5", "b6", "b7"]),
    "HARMONIC_MINOR": ("Harmonic Minor", [0, 2, 3, 5, 7, 8, 11], ["1", "2", "b3", "4", "5", "b6", "7"]),
    "MELODIC_MINOR": ("Melodic Minor", [0, 2, 3, 5, 7, 9, 11], ["1", "2", "b3", "4", "5", "6", "7"]),
    "DORIAN": ("Dorian Mode", [0, 2, 3, 5, 7, 9, 10], ["1", "2", "b3", "4", "5", "6", "b7"]),
    "PHRYGIAN": ("Phrygian Mode", [0, 1, 3, 5, 7, 8, 10], ["1", "b2", "b3", "4", "5", "b6", "b7"]),
    "LYDIAN": ("Lydian Mode", [0, 2, 4, 6, 7, 9, 11], ["1", "2", "3", "#4", "5", "6", "7"]),
    "MIXOLYDIAN": ("Mixolydian Mode", [0, 2, 4, 5, 7, 9, 10], ["1", "2", "3", "4", "5", "6", "b7"]),
    "LOCRIAN": ("Locrian Mode", [0, 1, 3, 5, 6, 8, 10], ["1", "b2", "b3", "4", "b5", "b6", "b7"]),
    "PENTATONIC_MAJOR": ("Major Pentatonic", [0, 2, 4, 7, 9], ["1", "2", "3", "5", "6"]),
    "PENTATONIC_MINOR": ("Minor Pentatonic", [0, 3, 5, 7, 10], ["1", "b3", "4", "5", "b7"]),
    "BLUES": ("Blues Scale", [0, 3, 5, 6, 7, 10], ["1", "b3", "4", "b5", "5", "b7"]),
    "WHOLE_TONE": ("Whole Tone Scale", [0, 2, 4, 6, 8, 10], ["1", "2", "3", "#4", "#5", "b7"]),
    "CHROMATIC": ("Chromatic Scale", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], ["1", "b2", "2", "b3", "3", "4", "b5", "5", "b6", "6", "b7", "7"]),
}


def normalize_root_name(raw_root: str) -> str:
    """Format root note with canonical capitalization (e.g. 'c#' -> 'C#', 'bb' -> 'Bb')."""
    if not raw_root:
        raise ValueError("Root note cannot be empty.")
    letter = raw_root[0].upper()
    accidental = raw_root[1:].replace("♯", "#").replace("♭", "b")
    return letter + accidental


def parse_chord_symbol(chord_symbol: str) -> tuple[str, str, str | None]:
    """Parse a chord string into (root, suffix, slash_bass)."""
    cleaned = chord_symbol.strip()
    if not cleaned:
        raise ValueError("Chord string is empty.")

    slash_bass: str | None = None
    if "/" in cleaned:
        parts = cleaned.split("/", 1)
        chord_part = parts[0].strip()
        bass_part = parts[1].strip()

        if chord_part.endswith("6") and bass_part == "9":
            cleaned = chord_part + "/9"
            slash_bass = None
        else:
            if not bass_part:
                raise ValueError(f"Invalid slash notation in '{chord_symbol}': missing bass note.")
            slash_bass = normalize_root_name(bass_part)
            cleaned = chord_part

    match = re.match(r"^([A-Ga-g][#b♯♭]?)(.*)$", cleaned)
    if not match:
        raise ValueError(
            f"Invalid chord format '{chord_symbol}'. Chords must start with a valid note (A-G, optionally # or b)."
        )

    raw_root, raw_suffix = match.groups()
    root = normalize_root_name(raw_root)
    suffix = raw_suffix.strip()

    return root, suffix, slash_bass


def spell_note_diatonic(root_letter: str, root_semitone: int, interval_semitone: int, interval_label: str) -> str:
    """Calculate the precise musical note name using diatonic scale letter steps and accidentals."""
    target_semitone = (root_semitone + interval_semitone) % 12
    degree = INTERVAL_DEGREE_MAP.get(interval_label)

    if degree is None:
        scale = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
        return scale[target_semitone]

    root_idx = DIATONIC_LETTERS.index(root_letter)
    target_letter_idx = (root_idx + degree - 1) % 7
    target_letter = DIATONIC_LETTERS[target_letter_idx]
    natural_semitone = NATURAL_SEMITONES[target_letter]

    diff = (target_semitone - natural_semitone) % 12
    if diff > 6:
        diff -= 12

    if diff == 0:
        return target_letter
    if diff == 1:
        return f"{target_letter}#"
    if diff == 2:
        return f"{target_letter}##"
    if diff == -1:
        return f"{target_letter}b"
    if diff == -2:
        return f"{target_letter}bb"

    return target_letter


def build_chord(chord_symbol: str) -> dict[str, Any]:
    """Compute notes, intervals, and structure for any chord symbol using interval theory."""
    root, suffix, slash_bass = parse_chord_symbol(chord_symbol)

    root_upper = root.upper()
    if root_upper not in NOTE_TO_SEMITONE:
        raise ValueError(f"Unrecognized root note '{root}'.")

    root_semitone = NOTE_TO_SEMITONE[root_upper]
    root_letter = root[0].upper()

    s_clean = suffix.replace(" ", "").replace("♯", "#").replace("♭", "b")

    if s_clean.startswith("m") and not s_clean.lower().startswith("maj") and not s_clean.lower().startswith("min"):
        normalized_suffix = "M" + s_clean[1:].upper()
    elif s_clean.startswith("M") and not s_clean.upper().startswith("MAJ") and not s_clean.upper().startswith("MIN"):
        normalized_suffix = "MAJ" + s_clean[1:].upper()
    else:
        normalized_suffix = s_clean.upper()

    if normalized_suffix not in CHORD_FORMULAS:
        available_examples = ["maj7", "m7", "7", "dim", "aug", "sus4", "sus2", "m7b5", "9", "maj9", "m9", "add9", "6/9"]
        raise ValueError(
            f"Unsupported chord quality/suffix '{suffix}' in '{chord_symbol}'. "
            f"Supported examples include: {', '.join(available_examples)} and slash chords (e.g. C/E)."
        )

    quality_name, intervals, formula_labels = CHORD_FORMULAS[normalized_suffix]

    chord_notes: list[str] = []
    for interval_semi, label in zip(intervals, formula_labels):
        chord_notes.append(spell_note_diatonic(root_letter, root_semitone, interval_semi, label))

    is_inversion = False
    inversion_type = None
    final_notes = list(chord_notes)

    if slash_bass:
        bass_upper = slash_bass.upper()
        if bass_upper not in NOTE_TO_SEMITONE:
            raise ValueError(f"Unrecognized slash bass note '{slash_bass}'.")

        bass_semitone = NOTE_TO_SEMITONE[bass_upper]

        matching_indices = [
            i for i, semi in enumerate(intervals)
            if (root_semitone + semi) % 12 == bass_semitone
        ]

        if matching_indices:
            is_inversion = True
            idx = matching_indices[0]
            matched_note = chord_notes[idx]
            final_notes = chord_notes[idx:] + chord_notes[:idx]
            inversion_type = f"Inversion starting on {matched_note} ({formula_labels[idx]})"
        else:
            final_notes = [slash_bass] + [n for n in chord_notes if n != slash_bass]
            inversion_type = f"Slash chord over {slash_bass} bass"

    return {
        "chord": chord_symbol,
        "root": root,
        "quality": quality_name,
        "formula": formula_labels,
        "notes": final_notes,
        "notes_str": " ".join(final_notes),
        "intervals_semitones": intervals,
        "slash_bass": slash_bass,
        "is_inversion": is_inversion,
        "inversion_details": inversion_type,
    }


def build_scale(root: str, scale_type: str = "major") -> dict[str, Any]:
    """Compute notes, intervals, and scale degrees for any scale/mode."""
    norm_root = normalize_root_name(root)
    root_upper = norm_root.upper()
    if root_upper not in NOTE_TO_SEMITONE:
        raise ValueError(f"Unrecognized root note '{root}'.")

    root_semitone = NOTE_TO_SEMITONE[root_upper]
    root_letter = norm_root[0].upper()

    clean_scale_key = scale_type.strip().upper().replace(" ", "_").replace("-", "_")
    if clean_scale_key not in SCALE_FORMULAS:
        available_scales = ["major", "minor", "harmonic_minor", "melodic_minor", "dorian", "phrygian", "lydian", "mixolydian", "pentatonic_major", "pentatonic_minor", "blues"]
        raise ValueError(
            f"Unsupported scale type '{scale_type}'. Available options: {', '.join(available_scales)}"
        )

    scale_name, intervals, degree_labels = SCALE_FORMULAS[clean_scale_key]

    scale_notes: list[str] = []
    for interval_semi, label in zip(intervals, degree_labels):
        scale_notes.append(spell_note_diatonic(root_letter, root_semitone, interval_semi, label))

    return {
        "root": norm_root,
        "scale_type": scale_type,
        "name": f"{norm_root} {scale_name}",
        "notes": scale_notes,
        "notes_str": " ".join(scale_notes),
        "formula": degree_labels,
        "intervals_semitones": intervals,
    }


def transpose_chord_logic(chord_symbol: str, semitones: int) -> dict[str, Any]:
    """Transpose a chord symbol by a given number of semitones."""
    root, suffix, slash_bass = parse_chord_symbol(chord_symbol)

    root_upper = root.upper()
    if root_upper not in NOTE_TO_SEMITONE:
        raise ValueError(f"Unrecognized root note '{root}'.")

    root_semitone = NOTE_TO_SEMITONE[root_upper]
    new_root_semi = (root_semitone + semitones) % 12

    prefer_flats = "b" in root or (semitones < 0 and "#" not in root)
    scale = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"] if prefer_flats else ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    new_root = scale[new_root_semi]

    new_slash: str | None = None
    if slash_bass:
        bass_upper = slash_bass.upper()
        if bass_upper not in NOTE_TO_SEMITONE:
            raise ValueError(f"Unrecognized slash bass note '{slash_bass}'.")
        bass_semi = NOTE_TO_SEMITONE[bass_upper]
        new_bass_semi = (bass_semi + semitones) % 12
        new_slash = scale[new_bass_semi]

    new_symbol = f"{new_root}{suffix}"
    if new_slash:
        new_symbol += f"/{new_slash}"

    chord_data = build_chord(new_symbol)
    return {
        "original_chord": chord_symbol,
        "transposed_chord": new_symbol,
        "semitones": semitones,
        "analysis": chord_data,
    }


# ==============================================================================
# 2. MODEL CONTEXT PROTOCOL (MCP) SERVER LAYER
# ==============================================================================

mcp = MCPServer("Piano Music MCP")


# ------------------------------------------------------------------------------
# MCP RESOURCES (Static / Read-only Context for LLMs and Clients)
# ------------------------------------------------------------------------------

@mcp.resource(
    "theory://chords/formulas",
    name="Piano Chord Formulas Reference",
    description="Music theory reference of supported chord formulas, degree labels, and semitone intervals",
    mime_type="application/json",
)
def get_chord_formulas_resource() -> str:
    """Return a structured JSON reference of all supported piano chord formulas."""
    summary: dict[str, Any] = {
        "title": "Piano Chord Formulas Reference",
        "description": "Standard interval patterns and scale degree formulas used for piano chord construction.",
        "categories": {
            "Triads": {
                "Major": {"formula": ["1", "3", "5"], "semitones": [0, 4, 7], "aliases": ["", "maj", "M"]},
                "Minor": {"formula": ["1", "b3", "5"], "semitones": [0, 3, 7], "aliases": ["m", "min", "-"]},
                "Diminished": {"formula": ["1", "b3", "b5"], "semitones": [0, 3, 6], "aliases": ["dim"]},
                "Augmented": {"formula": ["1", "3", "#5"], "semitones": [0, 4, 8], "aliases": ["aug", "+"]},
                "Suspended 2nd": {"formula": ["1", "2", "5"], "semitones": [0, 2, 7], "aliases": ["sus2"]},
                "Suspended 4th": {"formula": ["1", "4", "5"], "semitones": [0, 5, 7], "aliases": ["sus4", "sus"]},
            },
            "6th Chords": {
                "Major 6th": {"formula": ["1", "3", "5", "6"], "semitones": [0, 4, 7, 9], "aliases": ["6", "maj6"]},
                "Minor 6th": {"formula": ["1", "b3", "5", "6"], "semitones": [0, 3, 7, 9], "aliases": ["m6", "min6"]},
                "6/9": {"formula": ["1", "3", "5", "6", "9"], "semitones": [0, 4, 7, 9, 2], "aliases": ["6/9", "69"]},
            },
            "7th Chords": {
                "Dominant 7th": {"formula": ["1", "3", "5", "b7"], "semitones": [0, 4, 7, 10], "aliases": ["7", "dom7"]},
                "Major 7th": {"formula": ["1", "3", "5", "7"], "semitones": [0, 4, 7, 11], "aliases": ["maj7", "M7", "Δ7"]},
                "Minor 7th": {"formula": ["1", "b3", "5", "b7"], "semitones": [0, 3, 7, 10], "aliases": ["m7", "min7", "-7"]},
                "Diminished 7th": {"formula": ["1", "b3", "b5", "bb7"], "semitones": [0, 3, 6, 9], "aliases": ["dim7", "o7"]},
                "Half-Diminished 7th": {"formula": ["1", "b3", "b5", "b7"], "semitones": [0, 3, 6, 10], "aliases": ["m7b5", "ø", "half-dim"]},
                "Minor-Major 7th": {"formula": ["1", "b3", "5", "7"], "semitones": [0, 3, 7, 11], "aliases": ["mMaj7", "minMaj7"]},
            },
            "Extended Chords": {
                "Dominant 9th": {"formula": ["1", "3", "5", "b7", "9"], "semitones": [0, 4, 7, 10, 2], "aliases": ["9"]},
                "Major 9th": {"formula": ["1", "3", "5", "7", "9"], "semitones": [0, 4, 7, 11, 2], "aliases": ["maj9", "M9"]},
                "Minor 9th": {"formula": ["1", "b3", "5", "b7", "9"], "semitones": [0, 3, 7, 10, 2], "aliases": ["m9", "min9"]},
                "Dominant 11th": {"formula": ["1", "3", "5", "b7", "9", "11"], "semitones": [0, 4, 7, 10, 2, 5], "aliases": ["11"]},
                "Dominant 13th": {"formula": ["1", "3", "5", "b7", "9", "13"], "semitones": [0, 4, 7, 10, 2, 9], "aliases": ["13"]},
            },
            "Altered Dominants": {
                "7 Flat 5": {"formula": ["1", "3", "b5", "b7"], "semitones": [0, 4, 6, 10], "aliases": ["7b5"]},
                "7 Sharp 5": {"formula": ["1", "3", "#5", "b7"], "semitones": [0, 4, 8, 10], "aliases": ["7#5", "7+5", "7aug"]},
                "7 Flat 9": {"formula": ["1", "3", "5", "b7", "b9"], "semitones": [0, 4, 7, 10, 1], "aliases": ["7b9"]},
                "7 Sharp 9": {"formula": ["1", "3", "5", "b7", "#9"], "semitones": [0, 4, 7, 10, 3], "aliases": ["7#9"]},
            },
        },
    }
    return json.dumps(summary, indent=2)


# ------------------------------------------------------------------------------
# MCP TOOLS (Dynamic Callable Actions)
# ------------------------------------------------------------------------------

@mcp.tool()
def get_chord(chord: str) -> dict[str, Any]:
    """Calculate and return the piano notes, intervals, and music theory structure for any chord.

    Supports major, minor, diminished, augmented, sus2/4, 6ths, 7ths, 9ths, 11ths, 13ths,
    add chords, 6/9, altered dominants (7b5, 7#5, 7b9, 7#9), and slash chords / inversions.

    Args:
        chord: The chord symbol to look up (e.g. 'C', 'Cmaj7', 'Am7', 'F#m7b5', 'C/E', 'G7b9', 'Bb9').

    Returns:
        A dictionary with chord analysis including notes, root, quality, formula, and bass note structure.
    """
    try:
        return build_chord(chord)
    except ValueError as err:
        return {
            "error": str(err),
            "chord": chord,
            "status": "invalid_or_unsupported_chord",
        }


@mcp.tool()
def get_scale(root: str, scale_type: str = "major") -> dict[str, Any]:
    """Generate notes, degrees, and interval formulas for any musical scale or mode.

    Supports major (ionian), natural minor (aeolian), harmonic minor, melodic minor,
    dorian, phrygian, lydian, mixolydian, locrian, pentatonic major/minor, blues, and whole tone.

    Args:
        root: The root note of the scale (e.g. 'C', 'F#', 'Bb', 'A').
        scale_type: The scale type or mode (e.g. 'major', 'minor', 'dorian', 'harmonic_minor', 'blues').

    Returns:
        A dictionary with scale notes, formula, degrees, and semitone steps.
    """
    try:
        return build_scale(root, scale_type)
    except ValueError as err:
        return {
            "error": str(err),
            "root": root,
            "scale_type": scale_type,
            "status": "invalid_scale_request",
        }


@mcp.tool()
def transpose_chord(chord: str, semitones: int) -> dict[str, Any]:
    """Transpose any chord symbol up or down by a given number of semitones.

    Args:
        chord: The original chord symbol (e.g. 'Cmaj7', 'Am7', 'C/E').
        semitones: Number of semitones to shift (positive for pitch up, negative for down, e.g. 2, -3).

    Returns:
        A dictionary with the original chord, transposed chord symbol, and full note analysis.
    """
    try:
        return transpose_chord_logic(chord, semitones)
    except ValueError as err:
        return {
            "error": str(err),
            "chord": chord,
            "semitones": semitones,
            "status": "invalid_transpose_request",
        }


# ------------------------------------------------------------------------------
# MCP PROMPTS (Reusable Prompt Templates for LLMs and Users)
# ------------------------------------------------------------------------------

@mcp.prompt(
    name="analyze_chord",
    description="Reusable prompt template for analyzing a piano chord's notes, quality, formula, and performance context",
)
def analyze_chord(chord: str) -> str:
    """Generate a prompt template requesting a comprehensive analysis of a piano chord."""
    return f"""Please provide a comprehensive music theory and piano performance analysis for the chord '{chord}':

1. Chord Notes: List the exact piano notes contained in '{chord}'.
2. Chord Quality & Type: Explain the chord type (e.g. Major 7th, Half-Diminished, Altered Dominant).
3. Interval & Scale Formula: Detail the scale degrees (e.g., 1 - 3 - 5 - 7) and semitone intervals.
4. Piano Performance Explanation: Provide a concise explanation suitable for a piano player, including practical voice leading or fingering suggestions.
"""


# ==============================================================================
# 3. SERVER ENTRYPOINT
# ==============================================================================

if __name__ == "__main__":
    mcp.run()

