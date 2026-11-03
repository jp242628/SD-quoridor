"""Servidor do Quoridor: guarda o estado, valida as jogadas e expõe tudo via XML-RPC."""
import argparse
import threading
from socketserver import ThreadingMixIn
from xmlrpc.server import SimpleXMLRPCServer

from jogo import Jogo, NUM_JOGADORES

# Servidor XML-RPC multithread
class ServidorRPC(ThreadingMixIn, SimpleXMLRPCServer):
    """Servidor XML-RPC que atende cada chamada em uma thread, para vários clientes ao mesmo tempo."""
    daemon_threads = True

# Partida: sala de espera + partida em andamento
class Partida:
    """Sala de espera + partida. Os métodos públicos são as chamadas RPC."""

    # ---------- inicialização ----------
    def __init__(self):
        self.lock = threading.Lock()    # as threads do servidor compartilham o mesmo estado
        self.versao = 0
        self._reiniciar()

    def _reiniciar(self):
        self.jogo = Jogo()
        self.nomes = [""] * NUM_JOGADORES       # "" = vaga livre
        self.conectados = set()
        self.status = "aguardando"              # aguardando -> jogando -> fim
        self.mensagem = f"Aguardando jogadores (0/{NUM_JOGADORES})..."
        self.versao += 1

    # --------- chamadas RPC ----------
    def entrar(self, nome):
        # Adiciona um jogador à primeira vaga disponível.
        """Ocupa a primeira vaga livre. Retorna {'ok', 'id', 'msg'}."""
        with self.lock:
            if self.status != "aguardando":
                return {"ok": False, "id": -1, "msg": "Partida cheia ou já em andamento."}
            i = self.nomes.index("")
            self.nomes[i] = str(nome).strip()[:15] or f"Jogador {i + 1}"
            self.conectados.add(i)
            if len(self.conectados) == NUM_JOGADORES:
                self.status = "jogando"
                self.mensagem = f"Partida iniciada! Vez de {self.nomes[0]}."
            else:
                self.mensagem = f"Aguardando jogadores ({len(self.conectados)}/{NUM_JOGADORES})..."
            self.versao += 1
            print(f"{self.nomes[i]} entrou como jogador {i + 1}. {self.mensagem}")
            return {"ok": True, "id": i, "msg": "ok"}

    def estado(self, versao):
        # Retorna o estado apenas quando houve alguma alteração.
        """Se o cliente já tem a versão atual, responde só {'mudou': False}."""
        with self.lock:
            if versao == self.versao:
                return {"mudou": False}
            est = self.jogo.estado()
            est.update(mudou=True, versao=self.versao, status=self.status,
                       nomes=list(self.nomes), mensagem=self.mensagem)
            return est

    # --------- jogadas ----------
    def mover(self, jogador, linha, coluna):
        # Valida e registra uma tentativa de movimento.
        with self.lock:
            if self.status != "jogando":
                return {"ok": False, "msg": "A partida não está em andamento."}
            ok, msg = self.jogo.mover(jogador, (linha, coluna))
            return self._registrar(jogador, ok, msg)

    def parede(self, jogador, orientacao, linha, coluna):
        # Valida e registra uma tentativa de colocar parede.
        with self.lock:
            if self.status != "jogando":
                return {"ok": False, "msg": "A partida não está em andamento."}
            ok, msg = self.jogo.colocar_parede(jogador, orientacao, linha, coluna)
            return self._registrar(jogador, ok, msg)

    # --------- métodos auxiliares ----------
    def _registrar(self, jogador, ok, msg):
        """Atualiza mensagem e status depois de uma jogada e monta a resposta RPC."""
        if not ok:
            return {"ok": False, "msg": msg}
        nome = self.nomes[jogador]
        self.mensagem = f"{nome} {msg}."
        if self.jogo.vencedor != -1:
            self.status = "fim"
            self.mensagem += f" {nome} venceu a partida!"
        else:
            self.mensagem += f" Vez de {self.nomes[self.jogo.turno]}."
        self.versao += 1
        print(self.mensagem)
        return {"ok": True, "msg": self.mensagem}

    def sair(self, jogador):
        # Remove o jogador e encerra a partida se necessário.
        """Libera a vaga. Se a partida estava em andamento, ela é encerrada para todos."""
        with self.lock:
            if jogador not in self.conectados:
                return {"ok": True, "msg": "ok"}
            self.conectados.discard(jogador)
            nome = self.nomes[jogador]
            if self.status == "aguardando":
                self.nomes[jogador] = ""
                self.mensagem = f"Aguardando jogadores ({len(self.conectados)}/{NUM_JOGADORES})..."
            elif self.status == "jogando":
                self.status = "fim"
                self.mensagem = f"{nome} saiu: partida encerrada."
            self.versao += 1
            print(f"{nome} saiu.")
            if not self.conectados:
                self._reiniciar()               # sala vazia: pronta para uma nova partida
                print("Sala vazia: nova partida disponível.")
            return {"ok": True, "msg": "ok"}


def main():
    # Inicia o servidor XML-RPC e aguarda as chamadas dos clientes.
    ap = argparse.ArgumentParser(description="Servidor do Quoridor (XML-RPC)")
    ap.add_argument("--host", default="127.0.0.1",
                    help="endereço de escuta (use 0.0.0.0 para aceitar outras máquinas)")
    ap.add_argument("--porta", type=int, default=8000)
    args = ap.parse_args()

    partida = Partida()
    servidor = ServidorRPC((args.host, args.porta), logRequests=False)
    for nome in ("entrar", "estado", "mover", "parede", "sair"):
        servidor.register_function(getattr(partida, nome), nome)

    print(f"Servidor Quoridor em http://{args.host}:{args.porta} (Ctrl+C para encerrar)")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
