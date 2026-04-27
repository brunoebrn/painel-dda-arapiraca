# Template do arquivo local de configuração interna do pipeline.
#
# COMO USAR:
#   1. Copie este arquivo para v2/_internal_cache.py
#   2. Substitua o valor abaixo pelo token real, gerado uma única vez por:
#        python -c "import secrets; print(secrets.token_urlsafe(48))"
#   3. NÃO commite o _internal_cache.py (o .gitignore já bloqueia).
#   4. Faça backup do token em local seguro (gerenciador de senhas / OneDrive
#      pessoal). Sem o token, dados anonimizados anteriores não podem ser
#      reconciliados com novas extrações (paciente_id mudaria).
#
# IMPORTANTE:
#   Este token NÃO deve aparecer em logs, prints, conversas ou commits.
#   É o equivalente a uma chave privada de criptografia para os identificadores
#   anonimizados do painel.

CACHE_TOKEN = "REPLACE_WITH_LOCAL_TOKEN"
