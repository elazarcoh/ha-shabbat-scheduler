from datetime import time

import yaml

from custom_components.shabbat_scheduler.models import Action, EREV, Rule
from custom_components.shabbat_scheduler.yaml_io import export_yaml, import_yaml


def _rules():
    return [
        Rule(id="a", profile=1, day=EREV, time=time(23, 0), action=Action.OFF,
             devices=("climate.a",)),
        Rule(id="b", profile=1, day="1", time=time(11, 0), action=Action.ON,
             devices=("climate.a",), name="בוקר שבת"),
    ]


def test_export_groups_by_profile_and_day():
    parsed = yaml.safe_load(export_yaml({"temperature": 26}, _rules()))
    assert parsed["defaults"] == {"temperature": 26}
    assert set(parsed["profiles"]["1_day"]) == {"erev", "day_1"}
    assert parsed["profiles"]["1_day"]["erev"][0]["at"] == "23:00:00"
    assert parsed["profiles"]["1_day"]["day_1"][0]["name"] == "בוקר שבת"


def test_round_trip_preserves_rules():
    defaults, rules = import_yaml(export_yaml({"temperature": 26}, _rules()))
    assert defaults == {"temperature": 26}
    assert {(r.profile, r.day, r.time, r.action) for r in rules} == {
        (1, EREV, time(23, 0), Action.OFF),
        (1, "1", time(11, 0), Action.ON),
    }
    assert {r.id for r in rules} == {"a", "b"}


def test_export_writes_hebrew_unescaped_in_raw_text():
    text = export_yaml({"temperature": 26}, _rules())
    assert "בוקר שבת" in text
    assert "\\u" not in text


def test_export_orders_erev_before_numbered_days():
    keys = list(yaml.safe_load(export_yaml({}, _rules()))["profiles"]["1_day"])
    assert keys.index("erev") < keys.index("day_1")


def test_import_honours_existing_id():
    text = """
defaults: {}
profiles:
  2_day:
    day_2:
      - id: "existing-id"
        at: "18:00"
        action: "off"
        devices: [climate.a]
"""
    _defaults, rules = import_yaml(text)
    assert len(rules) == 1
    assert rules[0].id == "existing-id"


def test_import_generates_ids_when_absent():
    text = """
defaults: {}
profiles:
  2_day:
    day_2:
      - at: "18:00"
        action: "off"
        devices: [climate.a]
"""
    _defaults, rules = import_yaml(text)
    assert len(rules) == 1
    assert rules[0].id
    assert rules[0].profile == 2
    assert rules[0].day == "2"
    assert rules[0].time == time(18, 0)


def test_import_accepts_empty_document():
    defaults, rules = import_yaml("")
    assert defaults == {}
    assert rules == []
