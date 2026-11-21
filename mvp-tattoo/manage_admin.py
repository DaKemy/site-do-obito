"""Comandos locais para criar contas de desenvolvedor e trocar suas senhas."""
import argparse
from getpass import getpass

import psycopg2
from werkzeug.security import generate_password_hash

import app as app_module


def read_password():
    """Lê e confirma a senha sem exibi-la no terminal."""
    password = getpass('Senha administrativa (mínimo 8 caracteres): ')
    confirmation = getpass('Confirme a senha: ')
    if password != confirmation:
        raise ValueError('As senhas não coincidem.')
    if not 8 <= len(password) <= 128:
        raise ValueError('A senha deve ter entre 8 e 128 caracteres.')
    return password


def read_username():
    """Lê e valida o nome da conta administrativa."""
    username = input('Usuário administrativo: ').strip().lower()
    if not username or len(username) > 80:
        raise ValueError('O usuário deve conter entre 1 e 80 caracteres.')
    return username


def confirm_database_write(command, username):
    """Exige confirmação antes de alterar o banco configurado no ambiente."""
    action = 'criar' if command == 'create' else 'redefinir a senha de'
    print(
        f'Isso vai {action} a conta "{username}" no banco indicado por '
        'DATABASE_URL.'
    )
    confirmation = input('Continuar? (s/N): ').strip().lower()
    if confirmation not in {'s', 'sim'}:
        raise SystemExit('Operação cancelada. O banco não foi alterado.')


def create_admin(username, password):
    """Cria usuário administrativo armazenando somente o hash da senha."""
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
    """Atualiza a senha de uma conta existente e exige que ela seja encontrada."""
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
    """Interpreta `create` ou `reset-password` e executa a operação escolhida."""
    parser = argparse.ArgumentParser(
        description='Cria ou redefine uma conta do painel do desenvolvedor.'
    )
    commands = parser.add_subparsers(dest='command')
    create = commands.add_parser('create', help='Criar uma conta administrativa')
    create.add_argument('username', nargs='?')
    reset = commands.add_parser('reset-password', help='Redefinir uma senha administrativa')
    reset.add_argument('username', nargs='?')
    args = parser.parse_args()
    command = args.command or 'create'
    supplied_username = getattr(args, 'username', None)
    username = supplied_username.strip().lower() if supplied_username else read_username()
    if not username or len(username) > 80:
        raise ValueError('O usuário deve conter entre 1 e 80 caracteres.')

    password = read_password()
    confirm_database_write(command, username)
    app_module.init_db()
    if command == 'create':
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
