def field_formats_as_strings(field_formats: dict) -> dict[str, str]:
    return {str(key): str(value) for key, value in (field_formats or {}).items()}
