"""RED-first strict native TF publication orphan slot invariant (#34)."""
import unittest
from types import SimpleNamespace
from scripts.audit_unified_tf import assert_only_publication_slots_unsectioned


class FakeOslots:
    def __init__(self, nodes):
        self.nodes=nodes

    def s(self,node):
        return self.nodes[node]


def api_fixture(units, publication):
    groups={"book": (10,), "publication_line": publication}
    return SimpleNamespace(
        F=SimpleNamespace(
            otype=SimpleNamespace(maxSlot=4, s=lambda n: groups.get(n, ())),
            unit_layer=SimpleNamespace(v=lambda n: units.get(n)),
        ),
        E=SimpleNamespace(oslots=FakeOslots({10:(1,2),20:(3,),21:(4,)})),
    )


class PublicationOrphanAuditTests(unittest.TestCase):
    def test_four_source_sectionless_nodes_must_be_publication_only(self):
        api = api_fixture({3:"publication",4:"publication"}, (20,21))
        self.assertEqual(assert_only_publication_slots_unsectioned(api), 2)

    def test_unknown_sectionless_slot_rejected(self):
        api = api_fixture({3:"publication",4:"apparatus"}, (20,))
        with self.assertRaisesRegex(ValueError, "outside|publication"):
            assert_only_publication_slots_unsectioned(api)

    def test_publication_marker_in_wrong_layer_rejected(self):
        api = api_fixture({3:"publication",4:"morph"}, (20,21))
        with self.assertRaisesRegex(ValueError, "publication|layer"):
            assert_only_publication_slots_unsectioned(api)


if __name__ == "__main__":
    unittest.main()
