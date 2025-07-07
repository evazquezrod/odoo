from odoo import Command
from odoo.tests import common, new_test_user


class TestPrivateReadGroupingSets(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_user = new_test_user(cls.env, login='Base User', groups='base.group_user')

    def test_simple_read_grouping_sets(self):
        Model = self.env['test_read_group.aggregate']
        Partner = self.env['res.partner']
        partner_1 = Partner.create({'name': 'z_one'})
        partner_2 = Partner.create({'name': 'a_two'})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 1})
        Model.create({'key': 1, 'partner_id': partner_1.id, 'value': 2})
        Model.create({'key': 1, 'partner_id': partner_2.id, 'value': 3})
        Model.create({'key': 2, 'partner_id': partner_2.id, 'value': 4})
        Model.create({'key': 2, 'partner_id': partner_2.id})
        Model.create({'key': 2, 'value': 5})
        Model.create({'partner_id': partner_2.id, 'value': 5})
        Model.create({'value': 6})
        Model.create({})

        grouping_sets = [['key', 'partner_id'], ['key'], ['partner_id'], []]
        expected_result = [
            Model._read_group([], grouping_set, aggregates=['value:sum'])
            for grouping_set in grouping_sets
        ]

        with self.assertQueries(["""
            SELECT
                GROUPING(
                    "test_read_group_aggregate"."key",
                    "test_read_group_aggregate"."partner_id"
                ),
                "test_read_group_aggregate"."key",
                "test_read_group_aggregate"."partner_id",
                SUM("test_read_group_aggregate"."value")
            FROM
                "test_read_group_aggregate"
            GROUP BY
                GROUPING SETS (
                    ("test_read_group_aggregate"."key", "test_read_group_aggregate"."partner_id"),
                    ("test_read_group_aggregate"."key"),
                    ("test_read_group_aggregate"."partner_id"),
                    ()
                )
            ORDER BY
                "test_read_group_aggregate"."key" ASC,
                "test_read_group_aggregate"."partner_id" ASC
        """]):
            self.assertEqual(
                Model._read_grouping_sets([], grouping_sets, aggregates=['value:sum']),
                expected_result,
            )

        grouping_sets = [['key', 'partner_id'], ['key'], ['partner_id'], []]
        orders = ["partner_id, key", "key", 'partner_id', ""]
        expected_result = [
            Model._read_group([], grouping_set, aggregates=['value:sum'], order=order)
            for grouping_set, order in zip(grouping_sets, orders)
        ]

        # Forcing order with many2one, traverse use the order of the comodel (res.partner)
        with self.assertQueries(["""
            SELECT
                GROUPING(
                    "test_read_group_aggregate"."key",
                    "test_read_group_aggregate"."partner_id"
                ),
                "test_read_group_aggregate"."key",
                "test_read_group_aggregate"."partner_id",
                SUM("test_read_group_aggregate"."value")
            FROM
                "test_read_group_aggregate"
                LEFT JOIN "res_partner" AS "test_read_group_aggregate__partner_id" ON (
                    "test_read_group_aggregate"."partner_id" = "test_read_group_aggregate__partner_id"."id"
                )
            GROUP BY
                GROUPING SETS (
                    (
                        "test_read_group_aggregate"."key",
                        "test_read_group_aggregate"."partner_id",
                        "test_read_group_aggregate__partner_id"."complete_name",
                        "test_read_group_aggregate__partner_id"."id"
                    ),
                    ("test_read_group_aggregate"."key"),
                    (
                        "test_read_group_aggregate"."partner_id",
                        "test_read_group_aggregate__partner_id"."complete_name",
                        "test_read_group_aggregate__partner_id"."id"
                    ),
                    ()
                )
            ORDER BY
                "test_read_group_aggregate__partner_id"."complete_name" ASC,
                "test_read_group_aggregate__partner_id"."id" DESC,
                "test_read_group_aggregate"."key" ASC
        """]):
            self.assertEqual(
                Model._read_grouping_sets([], grouping_sets, aggregates=['value:sum'], order="partner_id, key"),
                expected_result,
            )

    def test_many2many_read_grouping_sets(self):
        User = self.env['test_read_group.user']
        mario, luigi = User.create([{'name': 'Mario'}, {'name': 'Luigi'}])
        tasks = self.env['test_read_group.task'].create([
            {   # both users
                'name': "Super Mario Bros.",
                'user_ids': [Command.set((mario + luigi).ids)],
            },
            {   # mario only
                'name': "Paper Mario",
                'user_ids': [Command.set(mario.ids)],
            },
            {   # luigi only
                'name': "Luigi's Mansion",
                'user_ids': [Command.set(luigi.ids)],
            },
            {   # no user
                'name': 'Donkey Kong',
            },
        ])

        # expected = ["""
            
        # """]
        # with self.assertQueries([expected]):
        domain = [('id', 'in', tasks.ids)]
        grouping_sets = [['user_ids', 'key'], ['key'], ['user_ids'], []]
        aggregates = ['name:array_agg', '__count', 'integer:sum']
        self.assertEqual(
            tasks._read_grouping_sets(domain, grouping_sets, aggregates),
            [
                tasks._read_group(domain, groupby, aggregates)
                for groupby in grouping_sets
            ],
        )

        # expected = """
            
        # """
        # with self.assertQueries([expected]):
        domain = [('id', 'in', tasks.ids)]
        grouping_sets = [['user_ids', 'key'], ['key'], ['user_ids'], []]
        aggregates = ['name:array_agg', '__count', 'integer:sum']
        order = "user_ids DESC, key"
        self.assertEqual(
            tasks._read_grouping_sets(domain, grouping_sets, aggregates, order),
            [
                tasks._read_group(domain, groupby, aggregates, order)
                for groupby in grouping_sets
            ],
        )


class TestFormattedReadGroupingSets(common.TransactionCase):
    pass