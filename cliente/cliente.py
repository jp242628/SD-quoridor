"""Cliente do Quoridor (terminal): desenha o estado recebido e envia as jogadas ao servidor via XML-RPC."""
import argparse
import os
import time
from xmlrpc.client import Error as ErroRPC, ServerProxy

LETRAS = "abcdefghi"
OBJETIVOS = ["a linha 9 (embaixo)", "a coluna a (esquerda)",
             "a linha 1 (em cima)", "a coluna i (direita)"]

AJUDA = """
Comandos:
  m <casa>         mover o peão, ex.: m e2 (vale passo, pulo e pulo diagonal)
  p <casa> <h|v>   colocar parede, ex.: p e3 h
                     h = horizontal: fica abaixo da casa e cobre também a casa da direita
                     v = vertical: fica à direita da casa e cobre também a casa de baixo
                     (casa de referência: colunas a-h, linhas 1-8)
  ?                ajuda
  q                sair (encerra a partida para todos)
"""


def nome_casa(pos):
    """[0, 4] -> 'e1'."""
    return f"{LETRAS[pos[1]]}{pos[0] + 1}"


def ler_casa(txt):
    """'e2' -> (1, 4). Levanta ValueError se não for uma casa válida."""
    if len(txt) != 2 or txt[0] not in LETRAS or txt[1] not in "123456789":
        raise ValueError(txt)
    return int(txt[1]) - 1, LETRAS.index(txt[0])


def desenhar(est):
    # Monta uma representação visual do tabuleiro.
    """Tabuleiro em ASCII: '=' são paredes horizontais e '|' paredes verticais."""
    h = {tuple(p) for p in est["h"]}
    v = {tuple(p) for p in est["v"]}
    peoes = {tuple(p): str(i + 1) for i, p in enumerate(est["pos"])}
    saida = ["    " + "".join(f" {x}  " for x in LETRAS)]
    for l in range(9):
        linha = f"{l + 1:>2}  "
        for c in range(9):
            linha += f" {peoes.get((l, c), '.')} "
            linha += "|" if (l, c) in v or (l - 1, c) in v else " "
        saida.append(linha)
        if l < 8:                                   # linha entre duas fileiras de casas
            sep = "    "
            for c in range(9):
                sep += "===" if (l, c) in h or (l, c - 1) in h else "   "
                if c < 8:
                    sep += "|" if (l, c) in v else ("=" if (l, c) in h else " ")
            saida.append(sep)
    return "\n".join(saida)


def mostrar(est, meu_id):
    # Limpa a tela e mostra o estado atual da partida.
    os.system("cls" if os.name == "nt" else "clear")
    print("=== QUORIDOR ===\n")
    if est["status"] != "aguardando":
        print(desenhar(est) + "\n")
    for i, nome in enumerate(est["nomes"]):
        marca = ">" if est["status"] == "jogando" and est["turno"] == i else " "
        eu = "  <- você" if i == meu_id else ""
        if est["status"] == "aguardando":
            print(f" {marca} {i + 1}. {nome or '(vaga livre)'}{eu}")
        else:
            print(f" {marca} {i + 1}. {nome:<15} em {nome_casa(est['pos'][i])}"
                  f"   paredes: {est['paredes'][i]}{eu}")
    print(f"\n{est['mensagem']}")
    if est["status"] == "jogando":
        print(f"Seu objetivo: chegar à {OBJETIVOS[meu_id]}. Digite ? para ver os comandos.")


def ler_jogada(proxy, meu_id):
    # Lê uma jogada do usuário e envia o comando ao servidor.
    """Lê um comando e envia ao servidor. Devolve False se o jogador quiser sair."""
    partes = input("Sua vez [m casa | p casa h/v | ? | q] > ").lower().split()
    if not partes:
        return True
    cmd, resto = partes[0], "".join(partes[1:])
    try:
        if cmd == "m":
            linha, coluna = ler_casa(resto)
            resp = proxy.mover(meu_id, linha, coluna)
        elif cmd == "p":
            linha, coluna = ler_casa(resto[:2])
            if resto[2:] not in ("h", "v"):
                raise ValueError(resto)
            resp = proxy.parede(meu_id, resto[2:], linha, coluna)
        elif cmd == "?":
            print(AJUDA)
            return True
        elif cmd == "q":
            return input("Isso encerra a partida para todos. Confirmar? (s/n) ").lower() != "s"
        else:
            raise ValueError(cmd)
    except ValueError:
        print("Comando inválido. Digite ? para ver a ajuda.")
        return True
    if not resp["ok"]:
        print(resp["msg"])
    return True


def jogar(proxy, meu_id, intervalo):
    # Atualiza o estado do jogo e controla o turno do jogador.
    est, versao = None, -1
    while True:
        novo = proxy.estado(versao)          # polling: o servidor só manda o estado se mudou
        if novo["mudou"]:
            est, versao = novo, novo["versao"]
            mostrar(est, meu_id)
            if est["status"] == "fim":
                return
        if est["status"] == "jogando" and est["turno"] == meu_id:
            if not ler_jogada(proxy, meu_id):
                return
        else:
            time.sleep(intervalo)


def main():
    # Configura o cliente e inicia a comunicação com o servidor.
    ap = argparse.ArgumentParser(description="Cliente do Quoridor")
    ap.add_argument("--servidor", default="127.0.0.1", help="endereço do servidor")
    ap.add_argument("--porta", type=int, default=8000)
    ap.add_argument("--intervalo", type=float, default=1.0,
                    help="segundos entre consultas ao servidor")
    args = ap.parse_args()

    proxy = ServerProxy(f"http://{args.servidor}:{args.porta}/")
    meu_id = -1
    try:
        nome = input("Seu nome: ")
        resp = proxy.entrar(nome)
        if not resp["ok"]:
            print(resp["msg"])
            return
        meu_id = resp["id"]
        jogar(proxy, meu_id, args.intervalo)
    except (KeyboardInterrupt, EOFError):
        print("\nSaindo...")
    except (OSError, ErroRPC) as e:
        print(f"Falha na comunicação com o servidor ({args.servidor}:{args.porta}): {e}")
    finally:
        if meu_id >= 0:
            try:
                proxy.sair(meu_id)
            except (OSError, ErroRPC):
                pass


if __name__ == "__main__":
    main()
