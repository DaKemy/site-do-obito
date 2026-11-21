"""Testes interativos da ferramenta administrativa sem conexão com banco."""
import os
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault('FLASK_SECRET_KEY', 'test-session-secret')
os.environ.setdefault('CPF_HASH_SECRET', 'test-cpf-hash-secret')

import manage_admin


class ManageAdminTests(unittest.TestCase):
    @patch('manage_admin.getpass', side_effect=['senha123', 'senha123'])
    def test_password_with_eight_characters_is_accepted(self, _getpass):
        self.assertEqual(manage_admin.read_password(), 'senha123')

    @patch('manage_admin.getpass', side_effect=['senha12', 'senha12'])
    def test_password_with_fewer_than_eight_characters_is_rejected(self, _getpass):
        with self.assertRaisesRegex(ValueError, 'entre 8 e 128 caracteres'):
            manage_admin.read_password()

    def test_interactive_create_prompts_and_confirms_before_database_write(self):
        with (
            patch.object(sys, 'argv', ['manage_admin.py']),
            patch('builtins.input', side_effect=['AdminUser', 's']),
            patch.object(manage_admin, 'read_password', return_value='senha-segura-123'),
            patch.object(manage_admin.app_module, 'init_db') as init_db,
            patch.object(manage_admin, 'create_admin') as create_admin,
        ):
            manage_admin.main()

        init_db.assert_called_once_with()
        create_admin.assert_called_once_with('adminuser', 'senha-segura-123')

    def test_declining_database_confirmation_makes_no_changes(self):
        with (
            patch.object(sys, 'argv', ['manage_admin.py']),
            patch('builtins.input', side_effect=['adminuser', 'n']),
            patch.object(manage_admin, 'read_password', return_value='senha-segura-123'),
            patch.object(manage_admin.app_module, 'init_db') as init_db,
            patch.object(manage_admin, 'create_admin') as create_admin,
        ):
            with self.assertRaisesRegex(SystemExit, 'banco não foi alterado'):
                manage_admin.main()

        init_db.assert_not_called()
        create_admin.assert_not_called()


if __name__ == '__main__':
    unittest.main()
