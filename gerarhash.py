import bcrypt

# --- COLOQUE SUA SENHA DESEJADA AQUI ---
nova_senha_texto = "Neon@2026" 

# Gerando o Hash
hash_gerado = bcrypt.hashpw(nova_senha_texto.encode('utf-8'), bcrypt.gensalt())

print("\n" + "="*30)
print("COPIE O CÓDIGO ABAIXO (INCLUINDO O 'b'):")
print(hash_gerado)
print("="*30)