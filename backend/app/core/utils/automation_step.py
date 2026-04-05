import re

_SUPPORTED_VARIABLES = {"prenom", "nom", "email", "telephone", "date_rdv", "calendrier"}


def resolve_variables(content: str, context: dict, trigger: str) -> str:
    """
    Replace {variable} placeholders in content with values from context.

    Rules:
    - {date_rdv} when trigger == 'coordonnees_sans_booking' → replaced with 'N/A'
    - {date_rdv} when context['date_rdv'] is None → replaced with 'N/A'
    - Unknown variables (not in supported set) are left unchanged.
    - Consecutive whitespace in the final string is collapsed to a single space.
    """
    replacements: dict[str, str] = {}

    for var in _SUPPORTED_VARIABLES:
        if var == "date_rdv":
            if trigger == "coordonnees_sans_booking" or context.get("date_rdv") is None:
                replacements["date_rdv"] = "N/A"
            else:
                replacements["date_rdv"] = str(context.get("date_rdv", "N/A"))
        else:
            value = context.get(var)
            if value is not None:
                replacements[var] = str(value)

    def replace_match(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in replacements:
            return replacements[var_name]
        # Unknown variable → leave as-is
        return match.group(0)

    result = re.sub(r"\{(\w+)\}", replace_match, content)

    # Collapse multiple consecutive whitespace characters
    result = re.sub(r" {2,}", " ", result).strip()

    return result
