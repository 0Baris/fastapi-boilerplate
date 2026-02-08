import re


def is_null(value):
    return value is None


def is_empty(value):
    return is_equals(value, "")


def is_null_or_empty(value):
    return is_null(value) or is_empty(value)


def is_equals(value, predicate):
    return value == predicate


def is_not_equals(value, predicate):
    return value != predicate


def has_length(value, predicate):
    return len(value) == predicate


def has_min_length(value, predicate):
    return len(value) < predicate


def has_max_length(value, predicate):
    return len(value) > predicate


def has_range_length(value, predicate_min, predicate_max):
    return has_min_length(value, predicate_min) and has_max_length(value, predicate_max)


def regex_is_valid(value: str, pattern: str) -> bool:
    try:
        reg = re.compile(pattern)
        return bool(reg.match(value))
    except:  # noqa
        return False


def is_regex(value: str) -> bool:
    if len(value) <= 0:
        return False
    try:
        re.compile(value)
        return True
    except:  # noqa
        return False


def is_file(value: str) -> bool:
    return regex_is_valid(value, r"^.*/(.*)\.(.*)$")  # "([a-zA-Z0-9\s_\\.\-\(\):])+.[\w]{2,4}$" # "^[\w-]+.[\w]{2,4}$"


def is_ipv4_cidr(value: str) -> bool:
    return regex_is_valid(value, r"(?<!\d\.)(?<!\d)(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}(?!\d|(?:\.\d))")


def is_ipv6_cidr(value: str) -> bool:
    return regex_is_valid(
        value,
        r"^s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:)))(%.+)?s*(\/([0-9]|[1-9][0-9]|1[0-1][0-9]|12[0-8]))?$",
    )


def is_ipv4_address(value: str) -> bool:
    return regex_is_valid(
        value,
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
    )


def is_ipv6_address(value: str) -> bool:
    return regex_is_valid(
        value,
        r"(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))",
    )


def is_url(value: str) -> bool:
    # return regex_is_valid(value, "^((http|https|ftp|ftps|www):\/\/)?([a-zA-Z0-9\~\!\@\#\$\%\^\&\*\(\)_\-\=\+\\\/\?\.\:\;\'\,]*)(\.)([a-zA-Z0-9\~\!\@\#\$\%\^\&\*\(\)_\-\=\+\\\/\?\.\:\;\'\,]+)")
    return regex_is_valid(
        value,
        r"(https?://(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?://(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})",
    )


def is_query_string(value: str) -> bool:
    return regex_is_valid(value, r"^\?([\w-]+(=[\w-]*)?(&[\w-]+(=[\w-]*)?)*)?$")


def is_fqdn(value: str) -> bool:
    value = value.replace("https://", "")
    value = value.replace("http://", "")
    value = value.replace("ftps://", "")
    value = value.replace("ftp://", "")
    return regex_is_valid(value, r"(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)")


def is_hostname(value: str) -> bool:  # FQDN
    try:
        # ^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$
        if len(value) > 255:
            return False

        if value[-1] == ".":
            value = value[:-1]

        allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)

        return all(allowed.match(x) for x in value.split("."))
    except:  # noqa
        return False


def is_email_address(value: str) -> bool:
    return regex_is_valid(
        value,
        r'^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$',
    )


def is_hash_md5(value: str) -> bool:
    return regex_is_valid(value, r"([a-fA-F\d]{32})")


def is_hash_sha256(value: str) -> bool:
    return regex_is_valid(value, r"\b[A-Fa-f0-9]{64}\b")


def is_hash_sha1(value: str) -> bool:
    if len(value) != 40:
        return False

    try:
        int(value, 16)
        return True

    except ValueError:
        return False
