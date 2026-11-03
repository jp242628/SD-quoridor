# Quoridor Distribuído

Versão distribuída do jogo Quoridor para 4 jogadores. Cada jogador usa um processo cliente separado, e todos se comunicam com um processo servidor por **RPC (XML-RPC)**, sem programar sockets diretamente. Trabalho da 1ª unidade de Sistemas Distribuídos.

## Estrutura

```
.
├── servidor/
│   ├── servidor.py   # processo servidor: sala de espera, turnos e funções RPC
│   └── jogo.py       # regras (tabuleiro, movimentos, paredes, BFS); não usa rede
└── cliente/
    └── cliente.py    # interface de terminal e chamadas RPC
```

## Como executar

Requer Python 3.8+ (somente biblioteca padrão, nada para instalar). Em Linux e macOS, use `python3` no lugar de `python`.

Abra 5 terminais na raiz do repositório:

```
python servidor/servidor.py     # terminal 1
python cliente/cliente.py       # terminais 2, 3, 4 e 5 (um por jogador)
```

A partida começa quando o 4º jogador entra.

**Outras máquinas:** inicie o servidor com `--host 0.0.0.0` e cada cliente com `--servidor IP_DO_SERVIDOR`.

**Porta ocupada:** a porta padrão é 8000 (`--porta`). Se aparecer erro de endereço já em uso (`Address already in use` no Linux/macOS), use outra porta no servidor e em todos os clientes, por exemplo:

```
python servidor/servidor.py --porta 8001
python cliente/cliente.py --porta 8001     # em cada terminal de jogador
```

## Como jogar

Os turnos seguem o sentido horário, na ordem de entrada: 1 (topo), 2 (direita), 3 (base) e 4 (esquerda). Vence quem chegar primeiro ao lado oposto do tabuleiro. A cada turno é preciso **mover o peão ou colocar uma parede**. Colunas são letras (a-i) e linhas são números (1-9).

| Comando | Efeito |
|---|---|
| `m e2` | move o peão para e2 (passo, pulo ou pulo diagonal) |
| `p e3 h` | parede horizontal abaixo de e3, cobrindo também f3 |
| `p e3 v` | parede vertical à direita de e3, cobrindo também e4 |
| `?` | ajuda |
| `q` | sai e encerra a partida para todos |

Na parede, a casa é só uma referência de posição: use colunas a-h e linhas 1-8.

## Regras implementadas

- Tabuleiro 9x9, 5 paredes por jogador (20 no total).
- O peão anda uma casa na ortogonal, sem atravessar paredes nem entrar em casa ocupada.
- Pulo: com um peão adjacente, pula-se sobre ele em linha reta. Se atrás dele houver parede, borda ou outro peão, pode-se ir para uma das casas ao lado dele (diagonal).
- Uma parede ocupa 2 casas e não pode sobrepor nem cruzar outra.
- Nenhuma parede pode fechar por completo o caminho de um jogador: a cada parede, o servidor roda uma BFS para os 4 peões.
- Quem não tiver nenhum lance possível (sem paredes e sem casas livres) tem a vez pulada.

## Arquitetura

- **Servidor autoritativo:** guarda o estado e valida todas as jogadas. Os clientes só enviam pedidos e desenham o que recebem.
- **Concorrência:** o servidor atende cada chamada RPC em uma thread (`ThreadingMixIn`) e um `Lock` protege o estado compartilhado.
- **Polling com versão:** o XML-RPC não permite o servidor chamar o cliente, então cada cliente chama `estado(versao)` a cada 1 s. Se nada mudou, o servidor responde só `{"mudou": false}`.

| Função RPC | O que faz |
|---|---|
| `entrar(nome)` | ocupa uma vaga e devolve o id do jogador (0 a 3) |
| `estado(versao)` | devolve o estado completo, ou só `mudou: false` se a versão for a mesma |
| `mover(id, linha, coluna)` | tenta mover o peão |
| `parede(id, orientacao, linha, coluna)` | tenta colocar uma parede |
| `sair(id)` | libera a vaga (durante a partida, encerra o jogo para todos) |

## Limitações

- Se um cliente cair sem avisar (processo encerrado à força), reinicie o servidor.
- Não há reconexão nem persistência: cada partida vive apenas enquanto o servidor estiver rodando.
