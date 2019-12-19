import random

alfabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz01234567890@#$_.*?=&%:<>+-[]"

def get_secret_key():
    shuffled = list(alfabet)
    random.shuffle(shuffled)
    shuffled = ''.join(shuffled)[10:-9]
    print("Secret Key:\n",shuffled)
    return shuffled

def valida_credenciales_token(usuario, password):
    return True