"""1D barcode code table (paper Sec. 2.1.1).

Each character is three bars. Each bar has a thickness class 1..5 (0.5-2.5 mm).
A label reads StartC · 4 payload characters · Stop = 18 bars.
"""

from __future__ import annotations

DECODING_SCHEME = {
    '123': 'Stop', '124': '0', '125': '1', '132': '2', '134': '3', '135': '4',
    '142': '5', '143': '6', '145': '7', '152': '8', '153': '9', '154': 'a',
    '213': 'b', '214': 'c', '215': 'd', '231': 'e', '234': 'f', '235': 'g',
    '241': 'h', '243': 'i', '245': 'j', '251': 'k', '253': 'l', '254': 'm',
    '312': 'n', '314': 'o', '315': 'p', '321': 'q', '324': 'r', '325': 's',
    '341': 't', '342': 'u', '345': 'v', '351': 'w', '352': 'x', '354': 'y',
    '412': 'z', '413': 'A', '415': 'B', '421': 'C', '423': 'D', '425': 'E',
    '431': 'F', '432': 'G', '435': 'H', '451': 'I', '452': 'J', '453': 'K',
    '512': 'L', '513': 'M', '514': 'N', '521': 'O', '523': 'P', '524': 'Q',
    '531': 'R', '532': 'S', '534': 'T', '541': 'U', '542': 'V', '543': 'StartC',
}
ENCODING_SCHEME = {v: k for k, v in DECODING_SCHEME.items()}

# Bar classes of the two physical labels used in the paper
LABEL_26 = [5, 4, 3, 1, 3, 4, 4, 2, 3, 1, 4, 3, 2, 5, 4, 1, 2, 3]       # Table 1 ("3D6m")
LABEL_1_LEWB = [5, 4, 3, 2, 5, 3, 2, 3, 1, 3, 5, 1, 2, 1, 3, 1, 2, 3]   # robustness sweep ("lewb")


def encode(payload: str) -> list[int]:
    """Bar classes for StartC + payload + Stop."""
    seq = ENCODING_SCHEME['StartC'] + ''.join(ENCODING_SCHEME[c] for c in payload) + ENCODING_SCHEME['Stop']
    return [int(c) for c in seq]


def decode(classes) -> tuple[str, bool]:
    """Decode a class sequence. Returns (payload, ok).

    Aligns on StartC (543) and reads to Stop (123). ``ok`` is True only for a
    clean StartC..Stop frame with no unknown symbol. Without a clean Stop, it returns
    a best-effort payload with ok=False.
    """
    s = ''.join(str(c) for c in classes)
    i = s.find('543')
    if i < 0:
        return '', False
    j = s.find('123', i)
    clean = j >= 0 and (j - i) % 3 == 0
    body = s[i:j + 3] if clean else s[i:len(s) - (len(s) - i) % 3]
    chars = [DECODING_SCHEME.get(body[k:k + 3], '?') for k in range(0, len(body), 3)]
    payload = ''.join(c for c in chars if c not in ('StartC', 'Stop') and len(c) == 1)
    return payload, clean and '?' not in chars
