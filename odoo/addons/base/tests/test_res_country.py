from odoo.tests import TransactionCase, tagged


class TestResCountryCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.glorious_arstotzka = cls.env['res.country'].create({
            'name': 'Arstotzka',
            'code': 'AA',
        })
        cls.altan = cls.env['res.country.state'].create({
            'country_id': cls.glorious_arstotzka.id,
            'code': 'AL',
            'name': 'Altan',
        })


@tagged('-at_install', 'post_install')
class TestResCountry(TestResCountryCommon):
    def test_name_search(self):
        glorious_arstotzka_tuple = (self.glorious_arstotzka.id, self.glorious_arstotzka.display_name)
        for (name, op) in [
            ('ARSTOTZKA', '='),
            ('arstotzka', '='),
            ('ARSTOTZKA', '!='),
            ('arstotzka', '!='),
            (['ARSTOTZKA'], 'in'),
            (['arstotzka'], 'in'),
            (['ARSTOTZKA'], 'not in'),
            (['arstotzka'], 'not in'),
            ('aA', '='),
            ('aA', '!='),
            (['aA'], 'in'),
            (['aA'], 'not in'),
        ]:
            with self.subTest((name, op)):
                if op in ('!=', 'not in'):
                    self.assertFalse(
                        glorious_arstotzka_tuple in
                        self.env['res.country'].name_search(name, operator=op),
                        f"Failed on: '{name} {op}'",
                    )
                else:
                    self.assertEqual(
                        self.env['res.country'].name_search(name, operator=op),
                        [glorious_arstotzka_tuple],
                        f"Failed on operator: '{name} {op}'",
                    )


@tagged('-at_install', 'post_install')
class TestResCountryState(TestResCountryCommon):
    def test_find_by_name(self):
        """It should be possible to find a state by its display name
        """
        glorious_arstotzka = self.glorious_arstotzka
        altan = self.altan

        for name in [
            altan.name,
            altan.display_name,
            'Altan(AA)',
            'Altan ( AA )',
            'Altan (Arstotzka)',
            'Altan (Arst)', # dubious
        ]:
            with self.subTest(name):
                self.assertEqual(
                    self.env['res.country.state'].name_search(name, operator='='),
                    [(altan.id, altan.display_name)]
                )

        # imitates basque provinces
        vescillo = self.env['res.country.state'].create({
            'country_id': glorious_arstotzka.id,
            'code': 'VE',
            'name': "Vescillo (Vesilo)",
        })
        for name in [
            vescillo.name,
            vescillo.display_name,
            "vescillo",
            "vesilo",
            "vescillo (AA)",
            "vesilo (AA)",
            "vesilo (Arstotzka)",
        ]:
            with self.subTest(name):
                # note operator for more flexible state name matching
                self.assertEqual(
                    self.env['res.country.state'].name_search(name, operator='ilike'),
                    [(vescillo.id, vescillo.display_name)]
                )

        # search in state list
        for name in [
            [altan.name],
            [altan.display_name],
            ['Altan(AA)'],
            ['Altan ( AA )'],
            ['Altan (Arstotzka)'],
            ['Altan (Arst)'],
        ]:
            with self.subTest(name):
                self.assertEqual(
                    self.env['res.country.state'].name_search(name, operator='in'),
                    [(altan.id, altan.display_name)]
                )
