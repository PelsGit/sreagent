import re
import unittest
from pathlib import Path


NETWORK_TF = Path(__file__).parents[2] / "infra" / "network.tf"


def resource_body(resource_type: str, name: str) -> str:
    source = NETWORK_TF.read_text()
    marker = f'resource "{resource_type}" "{name}" {{'
    start = source.index(marker) + len(marker)
    depth = 1
    cursor = start
    while depth:
        if source[cursor] == "{":
            depth += 1
        elif source[cursor] == "}":
            depth -= 1
        cursor += 1
    return source[start : cursor - 1]


class PrivateDnsDependencyTests(unittest.TestCase):
    def test_key_vault_app_link_depends_on_managed_zone(self):
        body = resource_body(
            "azurerm_private_dns_zone_virtual_network_link", "key_vault_app"
        )
        self.assertRegex(
            body,
            re.compile(r"private_dns_zone_name\s*=.*azurerm_private_dns_zone\.key_vault", re.S),
        )

    def test_acr_app_link_depends_on_managed_zone(self):
        body = resource_body(
            "azurerm_private_dns_zone_virtual_network_link", "acr_app"
        )
        self.assertRegex(
            body,
            re.compile(r"private_dns_zone_name\s*=.*azurerm_private_dns_zone\.acr", re.S),
        )


if __name__ == "__main__":
    unittest.main()
