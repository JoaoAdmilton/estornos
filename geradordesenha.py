import bcrypt

# Digite a senha que você deseja criar aqui
nova_senha = "SUA_NOVA_SENHA_AQUI" 

# Gera o hash seguro
hash_gerado = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt())

print(f"Copie este código: {hash_gerado}")