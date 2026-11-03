"""Regras do Quoridor para 4 jogadores.

Este módulo não conhece rede: o servidor apenas chama as funções daqui.
Posições são (linha, coluna) contadas a partir de 0; para o usuário, (0, 0) é "a1".
"""
from collections import deque

TAM = 9                                         # tabuleiro 9x9
NUM_JOGADORES = 4
PAREDES_INICIAIS = 5                            # 20 paredes no total, 5 por jogador
LETRAS = "abcdefghi"
DIRECOES = [(-1, 0), (1, 0), (0, -1), (0, 1)]   # cima, baixo, esquerda, direita

# Jogadores em sentido horário: topo, direita, base, esquerda
INICIO = [(0, 4), (4, 8), (8, 4), (4, 0)]


def nome_casa(pos):
    """(0, 4) -> 'e1'."""
    return f"{LETRAS[pos[1]]}{pos[0] + 1}"


def chegou_ao_objetivo(jogador, pos):
    """Cada jogador precisa alcançar o lado oposto ao de onde partiu."""
    linha, coluna = pos
    return (linha == TAM - 1, coluna == 0, linha == 0, coluna == TAM - 1)[jogador]


class Jogo:
    def __init__(self):
        self.pos = list(INICIO)
        self.paredes = [PAREDES_INICIAIS] * NUM_JOGADORES
        # Cada parede é identificada pela casa de referência (l, c):
        #   h: horizontal, fica abaixo da casa (l, c) e cobre as colunas c e c+1
        #   v: vertical, fica à direita da casa (l, c) e cobre as linhas l e l+1
        self.h = set()
        self.v = set()
        self.turno = 0
        self.vencedor = -1

    # ---------- consultas ----------

    def _passa(self, l, c, dl, dc):
        """Dá para andar de (l, c) até a vizinha (l+dl, c+dc)? Dentro do tabuleiro e sem parede."""
        nl, nc = l + dl, c + dc
        if not (0 <= nl < TAM and 0 <= nc < TAM):
            return False
        if dl:                                   # vertical: só paredes horizontais bloqueiam
            topo = min(l, nl)
            return (topo, c) not in self.h and (topo, c - 1) not in self.h
        esq = min(c, nc)                         # horizontal: só paredes verticais bloqueiam
        return (l, esq) not in self.v and (l - 1, esq) not in self.v

    def existe_caminho(self, jogador):
        # Verifica se o jogador ainda consegue chegar ao objetivo.
        """BFS: o peão ainda tem algum caminho até o objetivo? (outros peões não contam)"""
        inicio = self.pos[jogador]
        visitadas = {inicio}
        fila = deque([inicio])
        while fila:
            l, c = fila.popleft()
            if chegou_ao_objetivo(jogador, (l, c)):
                return True
            for dl, dc in DIRECOES:
                viz = (l + dl, c + dc)
                if viz not in visitadas and self._passa(l, c, dl, dc):
                    visitadas.add(viz)
                    fila.append(viz)
        return False

    def movimentos_validos(self, jogador):
        # Calcula todas as casas para onde o jogador pode se mover.
        """Casas de destino possíveis: passo simples, pulo reto ou pulo diagonal."""
        l, c = self.pos[jogador]
        ocupadas = set(self.pos)
        destinos = set()
        for dl, dc in DIRECOES:
            if not self._passa(l, c, dl, dc):
                continue
            vl, vc = l + dl, c + dc                      # casa vizinha
            if (vl, vc) not in ocupadas:
                destinos.add((vl, vc))
            elif self._passa(vl, vc, dl, dc) and (vl + dl, vc + dc) not in ocupadas:
                destinos.add((vl + dl, vc + dc))         # pulo reto sobre o adversário
            else:
                # pulo reto impossível (parede, borda ou outro peão atrás): vale o diagonal
                for pl, pc in ((dc, dl), (-dc, -dl)):    # direções perpendiculares
                    if self._passa(vl, vc, pl, pc) and (vl + pl, vc + pc) not in ocupadas:
                        destinos.add((vl + pl, vc + pc))
        return destinos

    def parede_valida(self, orient, l, c):
        # Confere se a parede pode ser colocada sem bloquear a partida.
        """Devolve (ok, mensagem de erro)."""
        if orient not in ("h", "v"):
            return False, "A orientação deve ser h ou v."
        if not (0 <= l < TAM - 1 and 0 <= c < TAM - 1):
            return False, "Parede fora do tabuleiro (use colunas a-h e linhas 1-8)."
        if orient == "h":
            mesmas, outras, lado = self.h, self.v, [(l, c - 1), (l, c + 1)]
        else:
            mesmas, outras, lado = self.v, self.h, [(l - 1, c), (l + 1, c)]
        # mesma posição, encaixe parcial (sobreposição) ou cruzamento no centro
        if (l, c) in mesmas or (l, c) in outras or any(p in mesmas for p in lado):
            return False, "Essa parede sobrepõe ou cruza outra parede."
        # coloca provisoriamente e confere se todos os peões ainda têm caminho
        mesmas.add((l, c))
        todos_com_caminho = all(self.existe_caminho(j) for j in range(NUM_JOGADORES))
        mesmas.discard((l, c))
        if not todos_com_caminho:
            return False, "Essa parede fecharia o caminho de um jogador."
        return True, ""

    # ---------- jogadas ----------

    def _erro_turno(self, jogador):
        if self.vencedor != -1:
            return "A partida já terminou."
        if jogador != self.turno:
            return "Não é a sua vez."
        return ""

    def mover(self, jogador, destino):
        # Executa um movimento válido e atualiza o turno.
        """Devolve (ok, descrição da jogada ou mensagem de erro)."""
        erro = self._erro_turno(jogador)
        if erro:
            return False, erro
        validos = self.movimentos_validos(jogador)
        if destino not in validos:
            lista = ", ".join(sorted(nome_casa(d) for d in validos))
            return False, f"Movimento inválido. Casas possíveis: {lista}"
        self.pos[jogador] = destino
        if chegou_ao_objetivo(jogador, destino):
            self.vencedor = jogador
        else:
            self._proximo_turno()
        return True, f"moveu para {nome_casa(destino)}"

    def colocar_parede(self, jogador, orient, l, c):
        # Coloca uma parede válida e passa a vez ao próximo jogador.
        """Devolve (ok, descrição da jogada ou mensagem de erro)."""
        erro = self._erro_turno(jogador)
        if erro:
            return False, erro
        if self.paredes[jogador] == 0:
            return False, "Você não tem mais paredes."
        ok, msg = self.parede_valida(orient, l, c)
        if not ok:
            return False, msg
        (self.h if orient == "h" else self.v).add((l, c))
        self.paredes[jogador] -= 1
        self._proximo_turno()
        tipo = "horizontal" if orient == "h" else "vertical"
        return True, f"colocou uma parede {tipo} em {nome_casa((l, c))}"

    def _proximo_turno(self):
        """Passa a vez; quem não tem nenhum lance possível (sem paredes e sem casas livres) é pulado."""
        for _ in range(NUM_JOGADORES):
            self.turno = (self.turno + 1) % NUM_JOGADORES
            if self.paredes[self.turno] > 0 or self.movimentos_validos(self.turno):
                return

    def estado(self):
        # Prepara o estado do jogo para ser enviado pela rede.
        """Estado em tipos simples (listas e números), que o XML-RPC consegue enviar."""
        return {
            "pos": [list(p) for p in self.pos],
            "paredes": list(self.paredes),
            "h": [list(p) for p in sorted(self.h)],
            "v": [list(p) for p in sorted(self.v)],
            "turno": self.turno,
            "vencedor": self.vencedor,
        }
