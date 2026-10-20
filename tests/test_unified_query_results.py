"""RED-first regression: TF Search may return lazy generators (#34)."""
import unittest
from types import SimpleNamespace

from scripts.smoke_unified_tf import collect_search_matches


class BoundedSearchResults(unittest.TestCase):
    def test_empty_generator_is_not_truthy_positive_match(self):
        calls = []
        def search(query, **kwargs):
            calls.append(kwargs)
            return (x for x in ())
        api = SimpleNamespace(S=SimpleNamespace(search=search))
        self.assertEqual(collect_search_matches(api, "word"), ())
        self.assertEqual(calls, [{"limit": 64}])

    def test_generator_is_materialized_only_up_to_bound(self):
        def search(query, **kwargs):
            return (tuple((i,)) for i in range(100))
        api = SimpleNamespace(S=SimpleNamespace(search=search))
        self.assertEqual(len(collect_search_matches(api, "word")), 64)


if __name__ == "__main__":
    unittest.main()
