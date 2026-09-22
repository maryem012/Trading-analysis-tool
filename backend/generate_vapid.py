"""
One-off VAPID key generator for Web Push (see alerts.py).

Run once per deployment:
    python generate_vapid.py

Paste both lines into backend/.env. The frontend doesn't need its own copy —
it fetches the public key at runtime from GET /api/push/vapid-public-key.
Never share the private key or commit it.
"""

import base64

from py_vapid import Vapid02


def main():
    v = Vapid02()
    v.generate_keys()

    # pywebpush wants the raw 32-byte private scalar, base64url, no padding
    priv_raw = v.private_key.private_numbers().private_value.to_bytes(32, "big")
    priv_b64 = base64.urlsafe_b64encode(priv_raw).rstrip(b"=").decode()

    # The browser's PushManager wants the uncompressed EC point (0x04 || x || y)
    pub_nums = v.public_key.public_numbers()
    pub_raw = b"\x04" + pub_nums.x.to_bytes(32, "big") + pub_nums.y.to_bytes(32, "big")
    pub_b64 = base64.urlsafe_b64encode(pub_raw).rstrip(b"=").decode()

    print(f"VAPID_PRIVATE_KEY={priv_b64}")
    print(f"VAPID_PUBLIC_KEY={pub_b64}")


if __name__ == "__main__":
    main()
