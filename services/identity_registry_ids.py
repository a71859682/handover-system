import re
import uuid
from typing import Callable, NoReturn


__all__ = (
    "IdentityRegistryIdValidationError",
    "validate_identity_registry_id",
    "generate_global_identity_id",
    "generate_login_identifier_alias_id",
    "generate_backend_principal_mapping_id",
)


_IDENTITY_REGISTRY_ID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.ASCII,
)
_VALIDATION_ERROR_MESSAGE = "invalid identity registry ID"
_UuidFactory = Callable[[], uuid.UUID]


class IdentityRegistryIdValidationError(ValueError):
    pass


def _raise_validation_error() -> NoReturn:
    raise IdentityRegistryIdValidationError(_VALIDATION_ERROR_MESSAGE)


def validate_identity_registry_id(value: object) -> str:
    if type(value) is not str:
        _raise_validation_error()
    if _IDENTITY_REGISTRY_ID_PATTERN.fullmatch(value) is None:
        _raise_validation_error()

    parse_failed = False
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, TypeError, ValueError):
        parse_failed = True
    if parse_failed:
        _raise_validation_error()

    if parsed.version != 4:
        _raise_validation_error()
    if parsed.variant != uuid.RFC_4122:
        _raise_validation_error()
    if str(parsed) != value:
        _raise_validation_error()
    return value


def _generate_identity_registry_id(uuid_factory: _UuidFactory) -> str:
    factory_failed = False
    try:
        generated = uuid_factory()
    except Exception:
        factory_failed = True
    if factory_failed:
        _raise_validation_error()

    if not isinstance(generated, uuid.UUID):
        _raise_validation_error()
    return validate_identity_registry_id(str(generated))


def generate_global_identity_id() -> str:
    return _generate_identity_registry_id(uuid.uuid4)


def generate_login_identifier_alias_id() -> str:
    return _generate_identity_registry_id(uuid.uuid4)


def generate_backend_principal_mapping_id() -> str:
    return _generate_identity_registry_id(uuid.uuid4)
