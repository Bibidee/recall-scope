# v0.2.0
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""Bounded administrator-managed registry of RecallScope signing keys."""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from genlayer import *


VERSION = "0.2.0"
MAX_AUTHORITIES = 32
MAX_ID = 96
MAX_NAME = 160
MAX_LIST = 8
MAX_ITEM = 160
RSA_MODULUS_HEX_LENGTH = 512


@allow_storage
@dataclass
class Authority:
    authority_id: str
    name: str
    signer_modulus: str
    signer_fingerprint: str
    domains: str
    markets: str
    products: str
    active: bool
    revision: u256
    created_at: u256
    revoked_at: u256


def _clean(value: str) -> str:
    return " ".join(str(value).replace("\x00", " ").split())


def _valid_id(value: str) -> str:
    result = str(value).strip()
    if len(result) == 0 or len(result) > MAX_ID or not re.match(r"^[A-Za-z0-9._:-]+$", result):
        raise gl.vm.UserError("[EXPECTED] Invalid authority_id")
    return result


def _valid_name(value: str) -> str:
    result = _clean(value)
    if len(result) == 0 or len(result) > MAX_NAME:
        raise gl.vm.UserError("[EXPECTED] Invalid authority name")
    return result


def _valid_list(value: str, label: str, domain_list: bool) -> str:
    raw = str(value).strip()
    items = raw.split("|")
    if len(items) < 1 or len(items) > MAX_LIST:
        raise gl.vm.UserError("[EXPECTED] Invalid " + label)
    normalized = []
    for item in items:
        token = item.strip().lower() if domain_list else _clean(item)
        if len(token) == 0 or len(token) > MAX_ITEM or "|" in token:
            raise gl.vm.UserError("[EXPECTED] Invalid " + label)
        if domain_list:
            if not re.match(r"^[a-z0-9-]+(?:\.[a-z0-9-]+)+$", token):
                raise gl.vm.UserError("[EXPECTED] Invalid allowed domain")
            if re.search(r"(^|\.)-", token) or re.search(r"-(\.|$)", token):
                raise gl.vm.UserError("[EXPECTED] Invalid allowed domain")
        elif not re.match(r"^[A-Za-z0-9][A-Za-z0-9 ._:/-]*$", token):
            raise gl.vm.UserError("[EXPECTED] Invalid " + label)
        if token in normalized:
            raise gl.vm.UserError("[EXPECTED] Duplicate " + label)
        normalized.append(token)
    return "|".join(normalized)


def _valid_modulus(value: str) -> str:
    result = str(value).strip().lower().removeprefix("0x")
    if len(result) != RSA_MODULUS_HEX_LENGTH or not re.match(r"^[0-9a-f]+$", result):
        raise gl.vm.UserError("[EXPECTED] RSA signer key must be a 2048-bit modulus")
    if result[0] not in "89abcdef" or result[-1] not in "13579bdf":
        raise gl.vm.UserError("[EXPECTED] Invalid RSA signer modulus")
    return "0x" + result


class RecallAuthorityRegistry(gl.Contract):
    admin: Address
    authorities: TreeMap[str, Authority]
    authority_count: u256

    def __init__(self):
        self.admin = gl.message.sender_address
        self.authority_count = u256(0)

    def _require_admin(self) -> None:
        if gl.message.sender_address != self.admin:
            raise gl.vm.UserError("[EXPECTED] Registry administrator only")

    @gl.public.write
    def register_authority(
        self,
        authority_id: str,
        name: str,
        signer_modulus: str,
        allowed_domains: str,
        allowed_markets: str,
        allowed_products: str,
    ) -> None:
        self._require_admin()
        key = _valid_id(authority_id)
        if self.authorities.get(key) is not None:
            raise gl.vm.UserError("[EXPECTED] Authority ID is immutable and already registered")
        if int(self.authority_count) >= MAX_AUTHORITIES:
            raise gl.vm.UserError("[EXPECTED] Authority capacity reached")
        name_value = _valid_name(name)
        modulus = _valid_modulus(signer_modulus)
        domains = _valid_list(allowed_domains, "allowed_domains", True)
        markets = _valid_list(allowed_markets, "allowed_markets", False)
        products = _valid_list(allowed_products, "allowed_products", False)
        fingerprint = "0x" + hashlib.sha256(modulus[2:].encode("ascii")).hexdigest()
        now = u256(int(datetime.now(timezone.utc).timestamp()))
        self.authorities[key] = Authority(
            key, name_value, modulus, fingerprint, domains, markets, products,
            True, u256(1), now, u256(0),
        )
        self.authority_count = u256(int(self.authority_count) + 1)

    @gl.public.write
    def revoke_authority(self, authority_id: str) -> None:
        self._require_admin()
        key = _valid_id(authority_id)
        authority = self.authorities.get(key)
        if authority is None or not authority.active:
            raise gl.vm.UserError("[EXPECTED] Active authority not found")
        authority.active = False
        authority.revoked_at = u256(int(datetime.now(timezone.utc).timestamp()))

    @gl.public.view
    def get_authority(self, authority_id: str) -> dict:
        authority = self.authorities.get(_valid_id(authority_id))
        if authority is None:
            return {}
        return {
            "authority_id": str(authority.authority_id),
            "name": str(authority.name),
            "signer_modulus": str(authority.signer_modulus),
            "signer_fingerprint": str(authority.signer_fingerprint),
            "domains": str(authority.domains),
            "markets": str(authority.markets),
            "products": str(authority.products),
            "active": bool(authority.active),
            "revision": int(authority.revision),
            "created_at": int(authority.created_at),
            "revoked_at": int(authority.revoked_at),
        }

    @gl.public.view
    def get_info(self) -> dict:
        return {
            "name": "RecallAuthorityRegistry",
            "version": VERSION,
            "admin": canonical_address_hex(self.admin),
            "max_authorities_lifetime": MAX_AUTHORITIES,
            "records_mutable": False,
            "revocation_irreversible": True,
            "signature_scheme": "RSA-2048-PKCS1-v1_5-SHA256",
        }


def canonical_address_hex(value) -> str:
    if isinstance(value, bytes):
        return "0x" + value.hex()
    return value.as_hex.lower()
