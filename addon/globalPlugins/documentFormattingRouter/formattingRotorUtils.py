INTEGER_DESCRIPTIONS = {
    "fontAttributeReporting": {
        0: "Off",
        1: "Speech",
        2: "Braille",
        3: "Speech and Braille"
    },
    "reportLineIndentation": {
        0: "Off",
        1: "Speech",
        2: "Tones",
        3: "Both Speech and Tones"
    },
    "reportTableHeaders": {
        0: "Off",
        1: "Rows and columns",
        2: "Rows",
        3: "Columns"
    },
    "reportCellBorders": {
        0: "Off",
        1: "Style",
        2: "Color and style"
    }
}

BITMASK_DESCRIPTIONS = {
    "reportSpellingErrors2": [
        (1, "Speech"),
        (2, "Sound"),
        (4, "Braille"),
    ],
}


def getNextConfigValue(config_key: str, value: int, validationArgs: tuple) -> int:
    if config_key in INTEGER_DESCRIPTIONS:
        values = sorted(INTEGER_DESCRIPTIONS[config_key])
        try:
            index = values.index(value)
        except ValueError:
            return values[0]
        return values[(index + 1) % len(values)]

    if config_key in BITMASK_DESCRIPTIONS:
        maxValue = sum(bit for bit, label in BITMASK_DESCRIPTIONS[config_key])
        if value < 0 or value >= maxValue:
            return 0
        return value + 1

    if len(validationArgs) >= 2:
        minValue, maxValue = validationArgs[:2]
        nextValue = value + 1
        if nextValue > int(maxValue):
            return int(minValue)
        return nextValue

    return value


def makeHumanReadableConfigValue(config_key: str, value: str | int) -> str:
    if config_key in BITMASK_DESCRIPTIONS and isinstance(value, int):
        enabledOptions = [
            label for bit, label in BITMASK_DESCRIPTIONS[config_key]
            if value & bit
        ]
        return ", ".join(enabledOptions) if enabledOptions else "Off"

    # Return "on" or "off" for boolean values.
    if isinstance(value, bool):
        return "checked" if value else "unchecked"

    # Return human-readable string for known integer settings.
    elif isinstance(value, int) and config_key in INTEGER_DESCRIPTIONS:
        return INTEGER_DESCRIPTIONS[config_key].get(value, "Unknown setting")

    # Fallback for out-of-range values.
    return str(value)
