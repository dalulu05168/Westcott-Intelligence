"""The alternate publisher cannot bypass the audited original/photo/ranking gate."""
import ast
from pathlib import Path
import unittest

class AlternateDeliveryGuardTests(unittest.TestCase):
    def test_direct_photo_route_is_blocked_before_network(self):
        source = Path(__file__).resolve().parents[2] / "telegram_news" / "dual_market.py"
        module = ast.parse(source.read_text())
        function = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "send_photo")
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), "exec"), namespace)
        with self.assertRaisesRegex(RuntimeError, "UNREVIEWED_ALTERNATE_DELIVERY_DISABLED"):
            namespace["send_photo"]("unused", "unused", b"", "image/png", "test")
