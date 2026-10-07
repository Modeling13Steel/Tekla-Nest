from __future__ import annotations

from collections import defaultdict

from tekla_nest.services.stock_rules import generate_default_stock
from video import model


def test_demo_model_members_stock_and_marks() -> None:
    payload = model.payload()
    members = payload["members"]
    assert 550 <= len(members) <= 650

    parts = model.parts()
    profile_pairs = {(p.profile, p.material) for p in parts}
    stock_pairs = {(s.profile, s.material) for s in generate_default_stock(sorted(profile_pairs))}
    assert profile_pairs <= stock_pairs

    by_mark = defaultdict(set)
    by_signature = defaultdict(set)
    for member in members:
        signature = (member["profile"], member["length"], member["material"])
        by_mark[member["mark"]].add(signature)
        by_signature[signature].add(member["mark"])
    assert all(len(signatures) == 1 for signatures in by_mark.values())
    assert all(len(marks) == 1 for marks in by_signature.values())
