from typing import Dict, List
from django.test import TestCase
from dynamic_preferences.users.registries import user_preferences_registry
from dynamic_preferences.types import BasePreferenceType

from mailcow_integration.dynamic_preferences_registry import alias_address_to_id, register_preferences

##################################################################################
# Test cases for email preferences
# @since 08 APR 2023
##################################################################################


class EmailPreferencesTest(TestCase):
    """Tests email preferences"""

    def _generate_preference_dict(self, name: str, is_public=False, allow_opt_out=True, default_opt=False) -> Dict:
        """Generates a preference dict. Its format is identical to how it would appear in mailcowconfig.json"""
        return {
            "title": name,
            "description": name,
            "internal": not is_public,
            "allow_opt_out": allow_opt_out,
            "default_opt": default_opt,
            "archive_addresses": [],
        }

    def test_alias_address_to_id(self):
        """Tests whether addresses are encoded to a format that dynamic preferences can use"""
        self.assertEqual(alias_address_to_id("foo@abc.example.com"), "fooabcexamplecom")

    def test_preferences_creation(self):
        """Tests the creation of mail preferences"""
        preferences = {
            "internal@example.com": self._generate_preference_dict("Internal"),
            "public@example.com": self._generate_preference_dict("PublicAlias", is_public=True),
            "noopt@example.com": self._generate_preference_dict("NoOpt", allow_opt_out=False),
            "defaultopt@example.com": self._generate_preference_dict("DefaultOpt", default_opt=True),
        }
        register_preferences(preferences)
        preferences: List[BasePreferenceType] = user_preferences_registry.preferences("mail")

        # Internal alias
        pref_name = alias_address_to_id("internal@example.com")
        internal_preference = next((pref for pref in preferences if pref.name == pref_name), None)
        self.assertIsNotNone(internal_preference)
        self.assertEqual(internal_preference.description, "Subscribed to internal@example.com")
        self.assertFalse(internal_preference.field_kwargs.get("disabled", True))
        self.assertFalse(internal_preference.default)
        self.assertIn("Internal", internal_preference.verbose_name)
        self.assertNotIn("Public", internal_preference.verbose_name)
        self.assertNotIn("Cannot opt-out", internal_preference.verbose_name)

        # Public Alias
        pref_name = alias_address_to_id("public@example.com")
        public_preference = next((pref for pref in preferences if pref.name == pref_name), None)
        self.assertIsNotNone(public_preference)
        self.assertIn("PublicAlias", public_preference.verbose_name)
        self.assertIn("Public", public_preference.verbose_name)

        # No opt-out Alias
        pref_name = alias_address_to_id("noopt@example.com")
        noopt_alias = next((pref for pref in preferences if pref.name == pref_name), None)
        self.assertIsNotNone(noopt_alias)
        self.assertIn("NoOpt", noopt_alias.verbose_name)
        self.assertIn("Cannot opt-out", noopt_alias.verbose_name)
        self.assertTrue(noopt_alias.field_kwargs.get("disabled", False))

        # Default opt-in alias
        pref_name = alias_address_to_id("defaultopt@example.com")
        defaultopt_alias = next((pref for pref in preferences if pref.name == pref_name), None)
        self.assertIsNotNone(defaultopt_alias)
        self.assertIn("DefaultOpt", defaultopt_alias.verbose_name)
        self.assertTrue(defaultopt_alias.default)
