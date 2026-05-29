"""Tests para poda de DOM móvil (interactables_index)."""
from __future__ import annotations

import unittest

from core.ui_automation.mobile_dom_parser import interactables_index_from_page_source


_SAMPLE_XML = """
<hierarchy>
  <android.widget.FrameLayout clickable="false">
    <android.widget.Button resource-id="com.app:id/login" text="Ingresar" clickable="true" class="android.widget.Button"/>
    <android.widget.EditText resource-id="com.app:id/user" clickable="true" class="android.widget.EditText"/>
  </android.widget.FrameLayout>
</hierarchy>
"""


class TestMobileDomParser(unittest.TestCase):
    def test_interactables_index_from_page_source(self) -> None:
        index = interactables_index_from_page_source(_SAMPLE_XML, max_elements=10)
        self.assertGreaterEqual(len(index), 1)
        ids = [item.get("resource_id") for item in index if item.get("resource_id")]
        self.assertTrue(any("login" in (rid or "") for rid in ids))

    def test_empty_xml_returns_empty_index(self) -> None:
        self.assertEqual(interactables_index_from_page_source(""), [])


if __name__ == "__main__":
    unittest.main()
