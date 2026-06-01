# ELIA License Tools

Generador **privado** de claves v4 (Ed25519 + TOTP). No se empaqueta en ELIA ni en PyInstaller.

## Requisitos

```bash
pip install -r license-tools/requirements.txt
```

## Configuración inicial (una vez)

```bash
python license-tools/setup_license_keys.py --update-repo
python license-tools/setup_license_totp.py
```

- La clave privada queda en `~/.elia/elia_license_private.pem` (permisos 600).
- La clave pública se añade a `core/license_public_keys.json` con un `kid` (rotación).
- El secreto TOTP queda en `~/.elia/license_totp.secret`.

## Emitir licencias

```bash
python license-tools/generate_license_key.py --machine <huella32hex> --tier professional --duration 365d
python license-tools/generate_license_key.py --beta-global
```

Formato: `ELIA-V4.{kid}.{payload_b64url}.{sig_b64url}` (puntos; el payload base64url puede contener `-`).

Duraciones: **15d**, **30d**, **365d** (no hay licencia permanente).

## Rotación de claves (`kid`)

1. `python license-tools/setup_license_keys.py --kid prod-2027 --update-repo`
2. Las claves antiguas siguen válidas mientras su `kid` permanezca en `license_public_keys.json`.

## TOTP

Antes de firmar, el generador pide el código de 6 dígitos. Solo desarrollo/CI:

```bash
set ELIA_LICENSE_TOTP_BYPASS=1
```

## Auditoría local

Emisiones append-only en `~/.elia/license_issued.log`.
