import argparse
from getpass import getpass

import psycopg2
from werkzeug.security import generate_password_hash

import app as app_module


def read_password():
    password = getpass('Senha administrativa (mínimo 12 caracteres): ')
    confirmation = getpass('Confirme a senha: ')
    if password != confirmation:
        raise ValueError('As senhas não coincidem.')
    if not 12 <= len(password) <= 128:
        raise ValueError('A senha deve ter entre 12 e 128 caracteres.')
    return password


def create_admin(username, password):
    conn = app_module.get_db()
    try:
        conn.execute(
            'INSERT INTO developer_admins (username, password_hash, role) '
            'VALUES (%s, %s, %s)',
            (username, generate_password_hash(password), 'developer'),
        )
        conn.commit()
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        conn.close()
        raise ValueError('Esse usuário administrativo já existe.') from None
    conn.close()


def reset_admin_password(username, password):
    conn = app_module.get_db()
    result = conn.execute(
        'UPDATE developer_admins SET password_hash = %s WHERE username = %s',
        (generate_password_hash(password), username),
    )
    if result.rowcount == 0:
        conn.close()
        raise ValueError('Usuário administrativo não encontrado.')
    conn.commit()
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Cria ou redefine uma conta do painel do desenvolvedor.'
    )
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('create', help='Criar uma conta administrativa')
    create.add_argument('username')
    reset = commands.add_parser('reset-password', help='Redefinir uma senha administrativa')
    reset.add_argument('username')
    args = parser.parse_args()
    username = args.username.strip().lower()
    if not username or len(username) > 80:
        parser.error('O usuário deve conter entre 1 e 80 caracteres.')

    password = read_password()
    app_module.init_db()
    if args.command == 'create':
        create_admin(username, password)
        print(f'Conta administrativa "{username}" criada.')
    else:
        reset_admin_password(username, password)
        print(f'Senha da conta administrativa "{username}" redefinida.')


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error)) from error
