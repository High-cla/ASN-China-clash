import ipaddress
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ChinaIP import collapse_cidrs, parse_cidr_lines  # type: ignore


def test_parse_skips_comments():
    lines = ["# c", "", "1.1.1.0/24", "not-a-cidr", "2001:db8::/32"]
    out = parse_cidr_lines(lines)
    assert "1.1.1.0/24" in [str(n) for n in out]
    assert any(str(n) == "2001:db8::/32" for n in out)
    assert not any(str(n) == "not-a-cidr" for n in out)


def test_collapse_merges_adjacent():
    nets = parse_cidr_lines(["1.1.1.0/25", "1.1.1.128/25"])
    collapsed = collapse_cidrs(nets)
    assert collapsed == ["1.1.1.0/24"]


if __name__ == "__main__":
    test_parse_skips_comments()
    test_collapse_merges_adjacent()
    print("ok")
