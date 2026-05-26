#!/usr/bin/env python3
"""Minimal greetd client — black TTY, 'Enter Password:', login → Hyprland.

Talks directly to greetd via $GREETD_SOCK (length-prefixed JSON over UNIX
socket). Single hard-coded user, no menus, no clock. Linux console renders
the blinking cursor for free.

If anything explodes, we exec /usr/bin/agreety as a safety net so we never
brick login.
"""
import os
import sys
import json
import struct
import socket
import getpass

USER = 'sirlexicon'
CMD = ['Hyprland']


def chat(sock, payload):
    data = json.dumps(payload).encode()
    sock.sendall(struct.pack('=I', len(data)) + data)

    hdr = b''
    while len(hdr) < 4:
        chunk = sock.recv(4 - len(hdr))
        if not chunk:
            raise IOError('greetd closed connection')
        hdr += chunk
    n = struct.unpack('=I', hdr)[0]

    body = b''
    while len(body) < n:
        chunk = sock.recv(n - len(body))
        if not chunk:
            raise IOError('greetd closed connection')
        body += chunk
    return json.loads(body.decode())


def clear():
    sys.stdout.write('\033[2J\033[H\033[?25h')
    sys.stdout.flush()


def prompt_password():
    sys.stdout.write('Enter Password:\n')
    sys.stdout.flush()
    return getpass.getpass('')


def attempt():
    sock_path = os.environ.get('GREETD_SOCK')
    if not sock_path:
        raise RuntimeError('GREETD_SOCK not set')

    s = socket.socket(socket.AF_UNIX)
    s.connect(sock_path)
    try:
        r = chat(s, {'type': 'create_session', 'username': USER})

        while r['type'] == 'auth_message':
            kind = r.get('auth_message_type', 'secret')
            if kind == 'secret':
                response = prompt_password()
            elif kind == 'visible':
                sys.stdout.write(r.get('auth_message', '') + '\n')
                sys.stdout.flush()
                response = input()
            else:
                # info / error → show, no input expected
                sys.stdout.write(r.get('auth_message', '') + '\n')
                sys.stdout.flush()
                response = ''
            r = chat(s, {'type': 'post_auth_message_response',
                         'response': response})

        if r['type'] == 'success':
            chat(s, {'type': 'start_session', 'cmd': CMD})
            return True

        try:
            chat(s, {'type': 'cancel_session'})
        except Exception:
            pass
        return False
    finally:
        s.close()


def main():
    while True:
        clear()
        try:
            if attempt():
                return
        except (KeyboardInterrupt, EOFError):
            continue
        # Wrong password / session error — clear and re-prompt


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never lock the user out — fall back to stock greetd greeter
        os.execvp('/usr/bin/agreety', ['agreety', '--cmd', 'Hyprland'])
