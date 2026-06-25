import secrets
from typing import List, Tuple

PRIME = 257


def _gf_mult(a: int, b: int) -> int:
    result = 0
    for _ in range(8):
        if b & 1:
            result ^= a
        carry = a & 0x80
        a = (a << 1) & 0xFF
        if carry:
            a ^= 0x1B
        b >>= 1
    return result


def _gf_inv(a: int) -> int:
    if a == 0:
        return 0
    for i in range(256):
        if _gf_mult(a, i) == 1:
            return i
    return 0


def _lagrange_interpolate(x: int, points: List[Tuple[int, int]], prime: int) -> int:
    result = 0
    for i, (xi, yi) in enumerate(points):
        num = 1
        den = 1
        for j, (xj, _) in enumerate(points):
            if i != j:
                num = (num * (x - xj)) % prime
                den = (den * (xi - xj)) % prime
        den_inv = pow(den, -1, prime)
        result = (result + yi * num * den_inv) % prime
    return result


def split_secret(secret: bytes, num_shares: int = 3, threshold: int = 3) -> List[bytes]:
    if threshold != 3 or num_shares != 3:
        raise ValueError("Only (3,3) scheme is supported")
    shares = [[] for _ in range(num_shares)]
    for byte_idx in range(len(secret)):
        s = secret[byte_idx]
        coeffs = [s] + [secrets.randbelow(PRIME) for _ in range(threshold - 1)]
        for share_idx in range(num_shares):
            x = share_idx + 1
            y = 0
            for power, coeff in enumerate(coeffs):
                y = (y + coeff * pow(x, power, PRIME)) % PRIME
            shares[share_idx].append(y)
    result = []
    for share in shares:
        flat = bytearray()
        for val in share:
            flat.extend(val.to_bytes(2, "big"))
        result.append(bytes(flat))
    return result


def reconstruct_secret(shares: List[bytes]) -> bytes:
    if len(shares) < 3:
        raise ValueError("Need exactly 3 shares to reconstruct")
    share_values = []
    for share in shares:
        if len(share) % 2 != 0:
            raise ValueError("Invalid share format")
        values = []
        for i in range(0, len(share), 2):
            values.append(int.from_bytes(share[i:i + 2], "big"))
        share_values.append(values)
    secret_len = len(share_values[0])
    for sv in share_values[1:]:
        if len(sv) != secret_len:
            raise ValueError("All shares must have the same length")
    points_list: List[List[Tuple[int, int]]] = [[] for _ in range(secret_len)]
    for share_idx, values in enumerate(share_values):
        x = share_idx + 1
        for byte_idx, val in enumerate(values):
            points_list[byte_idx].append((x, val))
    result = bytearray()
    for byte_idx in range(secret_len):
        val = _lagrange_interpolate(0, points_list[byte_idx], PRIME)
        result.append(val)
    return bytes(result)
