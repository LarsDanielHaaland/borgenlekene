import importlib

from django.db import migrations
from django.test import SimpleTestCase


class ActivityRankingRoundIdentityMigrationTests(SimpleTestCase):
    def test_old_unique_constraint_is_removed_before_legacy_rows_are_decoded(self):
        migration = importlib.import_module(
            "core.migrations.0010_activityranking_round_identity"
        )
        operations = migration.Migration.operations
        remove_unique_together = next(
            index
            for index, operation in enumerate(operations)
            if isinstance(operation, migrations.AlterUniqueTogether)
        )
        decode_legacy_rounds = next(
            index
            for index, operation in enumerate(operations)
            if isinstance(operation, migrations.RunPython)
        )

        self.assertLess(remove_unique_together, decode_legacy_rounds)
