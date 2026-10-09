"""Piano Music MCP Server - Music Intelligence Layer.

This server exposes Model Context Protocol (MCP) tools to analyze chords,
explore musical scales, and transpose chords using algorithmic music theory.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from mcp.server import MCPServer

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

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


# ==============================================================================
# MUSICBRAINZ EXTERNAL INTEGRATION & SEARCH TOOL
# ==============================================================================

MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2/recording/"
MUSICBRAINZ_USER_AGENT = "MusicIntelligenceMCP/1.1 ( contact@musicmcp.local; https://musicbrainz.org )"
MUSICBRAINZ_RATE_LIMIT_SECONDS = 1.1

_MB_RATE_FILE = Path(tempfile.gettempdir()) / "musicbrainz_rate_limit.timestamp"
_MB_RATE_LOCK = threading.Lock()


def _throttle_musicbrainz_request() -> None:
    """Enforce MusicBrainz rate limit policy (at least 1.1s between requests) across processes and threads."""
    with _MB_RATE_LOCK:
        now = time.time()
        last_time = 0.0
        try:
            if _MB_RATE_FILE.exists():
                content = _MB_RATE_FILE.read_text(encoding="utf-8").strip()
                if content:
                    last_time = float(content)
        except Exception:
            last_time = 0.0

        elapsed = now - last_time
        if elapsed < MUSICBRAINZ_RATE_LIMIT_SECONDS:
            sleep_needed = MUSICBRAINZ_RATE_LIMIT_SECONDS - elapsed
            time.sleep(sleep_needed)

        try:
            _MB_RATE_FILE.write_text(str(time.time()), encoding="utf-8")
        except Exception:
            pass


def _format_artist_credit(artist_credits: list[dict[str, Any]] | None) -> str:
    """Format an artist credit list into a readable artist name string."""
    if not artist_credits:
        return "Unknown Artist"
    parts: list[str] = []
    for item in artist_credits:
        name = item.get("name") or item.get("artist", {}).get("name", "")
        join = item.get("joinphrase", "")
        if name:
            parts.append(f"{name}{join}")
    return "".join(parts).strip() or "Unknown Artist"


def query_musicbrainz_recordings(query: str, limit: int = 5) -> dict[str, Any]:
    """Execute a search query against MusicBrainz recording endpoint with retries and rate limiting."""
    clean_query = query.strip()
    if not clean_query:
        return {
            "status": "empty_query",
            "message": "Search query cannot be empty.",
            "query": query,
            "count": 0,
            "results": [],
        }

    clamped_limit = max(1, min(limit, 25))
    max_retries = 3
    raw_data: dict[str, Any] | None = None
    last_error_message = "Unknown error"

    for attempt in range(max_retries):
        _throttle_musicbrainz_request()

        if HAS_REQUESTS:
            try:
                response = requests.get(
                    MUSICBRAINZ_API_URL,
                    params={
                        "query": clean_query,
                        "fmt": "json",
                        "limit": clamped_limit,
                    },
                    headers={
                        "User-Agent": MUSICBRAINZ_USER_AGENT,
                        "Accept": "application/json",
                    },
                    timeout=12.0,
                )

                if response.status_code == 200:
                    raw_data = response.json()
                    break
                elif response.status_code in (503, 429):
                    # Rate limit or temporary server busy; back off and retry
                    last_error_message = f"MusicBrainz HTTP {response.status_code}: Service Temporarily Busy"
                    if attempt < max_retries - 1:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    return {
                        "status": "http_error",
                        "error": "The MusicBrainz service is currently busy or rate-limited. Please try again shortly.",
                        "query": clean_query,
                        "count": 0,
                        "results": [],
                    }
                else:
                    return {
                        "status": "http_error",
                        "error": f"MusicBrainz HTTP {response.status_code}: {response.reason}",
                        "query": clean_query,
                        "count": 0,
                        "results": [],
                    }
            except requests.exceptions.Timeout:
                last_error_message = "Request to MusicBrainz API timed out."
                if attempt < max_retries - 1:
                    time.sleep(1.0)
                    continue
                return {
                    "status": "timeout",
                    "error": "Request to MusicBrainz API timed out after 12 seconds.",
                    "query": clean_query,
                    "count": 0,
                    "results": [],
                }
            except requests.exceptions.RequestException as err:
                return {
                    "status": "network_error",
                    "error": f"Network error contacting MusicBrainz: {str(err)}",
                    "query": clean_query,
                    "count": 0,
                    "results": [],
                }
            except ValueError as err:
                return {
                    "status": "invalid_response",
                    "error": f"Failed to parse MusicBrainz JSON response: {str(err)}",
                    "query": clean_query,
                    "count": 0,
                    "results": [],
                }
            except Exception as err:
                return {
                    "status": "error",
                    "error": f"Unexpected error during search: {str(err)}",
                    "query": clean_query,
                    "count": 0,
                    "results": [],
                }
        else:
            # Fallback using urllib.request
            params = urllib.parse.urlencode({
                "query": clean_query,
                "fmt": "json",
                "limit": clamped_limit,
            })
            target_url = f"{MUSICBRAINZ_API_URL}?{params}"
            req = urllib.request.Request(
                target_url,
                headers={
                    "User-Agent": MUSICBRAINZ_USER_AGENT,
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    payload = resp.read().decode("utf-8")
                    raw_data = json.loads(payload)
                    break
            except urllib.error.HTTPError as err:
                if err.code in (503, 429) and attempt < max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return {
                    "status": "http_error",
                    "error": f"MusicBrainz HTTP {err.code}: {err.reason}",
                    "query": clean_query,
                    "count": 0,
                    "results": [],
                }
            except (TimeoutError, socket.timeout):
                if attempt < max_retries - 1:
                    time.sleep(1.0)
                    continue
                return {
                    "status": "timeout",
                    "error": "Request to MusicBrainz API timed out.",
                    "query": clean_query,
                    "count": 0,
                    "results": [],
                }
            except urllib.error.URLError as err:
                return {
                    "status": "network_error",
                    "error": f"Network error contacting MusicBrainz: {err.reason}",
                    "query": clean_query,
                    "count": 0,
                    "results": [],
                }
            except Exception as err:
                return {
                    "status": "error",
                    "error": f"Unexpected error during search: {str(err)}",
                    "query": clean_query,
                    "count": 0,
                    "results": [],
                }

    if raw_data is None:
        return {
            "status": "http_error",
            "error": last_error_message,
            "query": clean_query,
            "count": 0,
            "results": [],
        }

    raw_recordings: list[dict[str, Any]] = raw_data.get("recordings", [])
    if not raw_recordings:
        return {
            "status": "no_results",
            "message": f"No music recordings found for query '{clean_query}'.",
            "query": clean_query,
            "count": 0,
            "results": [],
        }

    results: list[dict[str, Any]] = []
    for rec in raw_recordings:
        releases = rec.get("releases", [])
        primary_release = releases[0] if releases else {}

        results.append({
            "id": rec.get("id"),
            "title": rec.get("title", "Untitled"),
            "artist": _format_artist_credit(rec.get("artist-credit")),
            "release": primary_release.get("title"),
            "release_date": primary_release.get("date") or rec.get("first-release-date"),
            "length_ms": rec.get("length"),
            "score": rec.get("score"),
            "disambiguation": rec.get("disambiguation") or None,
        })

    return {
        "status": "success",
        "query": clean_query,
        "count": len(results),
        "results": results,
    }


@mcp.tool()
def search_music(query: str, limit: int = 5) -> dict[str, Any]:
    """Search MusicBrainz for matching music recordings, artists, albums, and metadata.

    Queries the public MusicBrainz Web Service API (v2) without requiring an API key.
    Adheres to the MusicBrainz rate limit policy and returns structured music metadata
    including recording title, artist, release/album, release date, duration,
    and MusicBrainz recording ID.

    Args:
        query: Song title, artist name, or search query (e.g. 'Bohemian Rhapsody', 'Clair de Lune', 'artist:Queen').
        limit: Maximum number of results to return (default 5, up to 25).

    Returns:
        A dictionary containing query status, count, and structured matching recording records.
    """
    return query_musicbrainz_recordings(query, limit)


def fetch_song_details_from_musicbrainz(recording_id: str) -> dict[str, Any]:
    """Fetch and structure comprehensive metadata, composition info, relationships, and releases for a recording."""
    clean_id = recording_id.strip()
    if not clean_id:
        return {
            "status": "invalid_id",
            "message": "Recording ID cannot be empty.",
            "recording_id": recording_id,
        }

    url = f"{MUSICBRAINZ_API_URL}{clean_id}?inc=artists+releases+work-rels+artist-rels+work-level-rels+media&fmt=json"
    max_retries = 3
    raw_data: dict[str, Any] | None = None
    last_error_message = "Unknown error"

    for attempt in range(max_retries):
        _throttle_musicbrainz_request()

        if HAS_REQUESTS:
            try:
                response = requests.get(
                    url,
                    headers={
                        "User-Agent": MUSICBRAINZ_USER_AGENT,
                        "Accept": "application/json",
                    },
                    timeout=12.0,
                )
                if response.status_code == 200:
                    raw_data = response.json()
                    break
                elif response.status_code in (503, 429):
                    last_error_message = f"MusicBrainz HTTP {response.status_code}: Service Temporarily Busy"
                    if attempt < max_retries - 1:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    return {
                        "status": "http_error",
                        "error": "The MusicBrainz service is currently busy. Please try again shortly.",
                        "recording_id": clean_id,
                    }
                elif response.status_code == 404:
                    return {
                        "status": "not_found",
                        "error": f"Recording ID '{clean_id}' not found on MusicBrainz.",
                        "recording_id": clean_id,
                    }
                else:
                    return {
                        "status": "http_error",
                        "error": f"MusicBrainz HTTP {response.status_code}: {response.reason}",
                        "recording_id": clean_id,
                    }
            except requests.exceptions.Timeout:
                last_error_message = "Request to MusicBrainz API timed out."
                if attempt < max_retries - 1:
                    time.sleep(1.0)
                    continue
                return {
                    "status": "timeout",
                    "error": "Request to MusicBrainz API timed out after 12 seconds.",
                    "recording_id": clean_id,
                }
            except requests.exceptions.RequestException as err:
                return {
                    "status": "network_error",
                    "error": f"Network error contacting MusicBrainz: {str(err)}",
                    "recording_id": clean_id,
                }
            except ValueError as err:
                return {
                    "status": "invalid_response",
                    "error": f"Failed to parse MusicBrainz JSON response: {str(err)}",
                    "recording_id": clean_id,
                }
            except Exception as err:
                return {
                    "status": "error",
                    "error": f"Unexpected error retrieving song details: {str(err)}",
                    "recording_id": clean_id,
                }
        else:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": MUSICBRAINZ_USER_AGENT,
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    raw_data = json.loads(resp.read().decode("utf-8"))
                    break
            except urllib.error.HTTPError as err:
                if err.code in (503, 429) and attempt < max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return {
                    "status": "http_error",
                    "error": f"MusicBrainz HTTP {err.code}: {err.reason}",
                    "recording_id": clean_id,
                }
            except Exception as err:
                return {
                    "status": "error",
                    "error": str(err),
                    "recording_id": clean_id,
                }

    if raw_data is None:
        return {
            "status": "http_error",
            "error": last_error_message,
            "recording_id": clean_id,
        }

    title = raw_data.get("title", "Untitled")
    artist = _format_artist_credit(raw_data.get("artist-credit"))
    first_release_date = raw_data.get("first-release-date")
    length_ms = raw_data.get("length")

    duration_formatted = None
    if length_ms:
        total_sec = length_ms // 1000
        mins = total_sec // 60
        secs = total_sec % 60
        duration_formatted = f"{mins}:{secs:02d}"

    work_info: dict[str, Any] | None = None
    composers: list[str] = []
    lyricists: list[str] = []
    arrangers: list[str] = []
    composition_date: str | None = None
    performance_date: str | None = None

    for rel in raw_data.get("relations", []):
        rel_type = rel.get("type")
        target_type = rel.get("target-type")

        # Check performance / recording dates
        if rel_type in ("performance", "recorded at", "recording location", "live"):
            if rel.get("begin") and not performance_date:
                performance_date = rel.get("begin")

        # Direct recording artist relations
        if target_type == "artist":
            artist_name = rel.get("artist", {}).get("name")
            if artist_name:
                if rel_type == "composer" and artist_name not in composers:
                    composers.append(artist_name)
                    if rel.get("begin") or rel.get("end"):
                        composition_date = rel.get("end") or rel.get("begin")
                elif rel_type in ("lyricist", "writer") and artist_name not in lyricists:
                    lyricists.append(artist_name)
                elif rel_type == "arranger" and artist_name not in arrangers:
                    arrangers.append(artist_name)

        # Linked Work
        if target_type == "work" or rel.get("work"):
            w = rel.get("work", {})
            work_id = w.get("id")
            if work_id and not work_info:
                work_info = {
                    "id": work_id,
                    "title": w.get("title") or title,
                    "disambiguation": w.get("disambiguation") or None,
                    "url": f"https://musicbrainz.org/work/{work_id}",
                }
            for wr in w.get("relations", []):
                wr_type = wr.get("type")
                wr_artist = wr.get("artist", {}).get("name")
                if wr_artist:
                    if wr_type == "composer" and wr_artist not in composers:
                        composers.append(wr_artist)
                        if wr.get("begin") or wr.get("end"):
                            composition_date = wr.get("end") or wr.get("begin")
                    elif wr_type in ("lyricist", "writer") and wr_artist not in lyricists:
                        lyricists.append(wr_artist)
                    elif wr_type == "arranger" and wr_artist not in arrangers:
                        arrangers.append(wr_artist)

    # Documented releases
    releases: list[dict[str, Any]] = []
    for rel in raw_data.get("releases", []):
        media = rel.get("media", [])
        format_name = media[0].get("format") if media else None
        releases.append({
            "id": rel.get("id"),
            "title": rel.get("title", "Untitled"),
            "date": rel.get("date") or "Unknown",
            "country": rel.get("country") or "Unknown",
            "status": rel.get("status") or "Official",
            "format": format_name,
        })

    # Clear status of documented vs missing information
    data_notes: dict[str, str] = {}
    if not composers:
        data_notes["composer"] = "Not documented in MusicBrainz relationships"
    if not work_info:
        data_notes["work"] = "No linked composition work in MusicBrainz"
    if not composition_date:
        data_notes["composition_date"] = "Original composition date not documented in MusicBrainz (distinct from release date)"
    if not performance_date:
        data_notes["performance_date"] = "Specific performance/recording date not documented in MusicBrainz"
    if not first_release_date:
        data_notes["first_release_date"] = "First release date not documented in MusicBrainz"

    return {
        "status": "success",
        "id": clean_id,
        "title": title,
        "artist": artist,
        "composers": composers,
        "lyricists": lyricists,
        "arrangers": arrangers,
        "work": work_info,
        "composition_date": composition_date,
        "performance_date": performance_date,
        "first_release_date": first_release_date,
        "duration_ms": length_ms,
        "duration_formatted": duration_formatted,
        "releases_count": len(releases),
        "releases": releases[:10],
        "source_url": f"https://musicbrainz.org/recording/{clean_id}",
        "data_notes": data_notes,
    }


@mcp.tool()
def get_song_details(recording_id: str) -> dict[str, Any]:
    """Retrieve comprehensive song details, composition metadata, relationships, and release history for a MusicBrainz recording.

    Queries the public MusicBrainz Web Service API (v2) for a specific recording ID,
    extracting composer/songwriter credits, linked work/composition title, composition date,
    performance date, first release date, album releases, and direct MusicBrainz source links.

    Args:
        recording_id: The MusicBrainz recording UUID (e.g. '01d2788d-862f-4d00-aa1e-f326a0d353a6').

    Returns:
        Structured dictionary containing song title, artist, composers, linked work, dates, releases, and source links.
    """
    return fetch_song_details_from_musicbrainz(recording_id)


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

