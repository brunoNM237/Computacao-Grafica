"""Malha OFF: normais, coordenadas de textura e enquadramento.

Tres formas de enviar a mesma malha para a GPU:

  suave()     -- indexada, uma normal por vertice (v2)
  facetada()  -- nao indexada, uma normal por face (v2)
  texturada() -- indexada, com coordenada de textura e
                 tangente (v3)
"""
from pathlib import Path

import glm
import numpy as np

EPS = 1e-12           # evita divisao por zero ao normalizar
TANGENTE_MIN = 1e-9   # abaixo disso, o vertice nao tem tangente
MEIA_VOLTA = 0.5      # em u; um triangulo comum cobre menos que isso

# Eixo polar do mapeamento (tecla E): a permutacao ciclica das
# coordenadas que leva esse eixo para a posicao de y. Uma
# permutacao ciclica e uma rotacao; a textura nao sai espelhada.
EIXOS = {"y": [0, 1, 2], "z": [1, 2, 0], "x": [2, 0, 1]}


class Malha:
    def __init__(self, caminho, ponderar_por_area=True):
        self.caminho = Path(caminho)
        self.vertices, self.faces = ler_off(self.caminho)
        # Esfera envolvente: centro da caixa e vertice mais afastado.
        minimo = self.vertices.min(axis=0)
        maximo = self.vertices.max(axis=0)
        self.centro = 0.5 * (minimo + maximo)
        self.raio = float(np.linalg.norm(self.vertices - self.centro,
                                         axis=1).max())
        self.normais_face = normais_de_face(self.vertices, self.faces)
        self.normais_vertice = normais_de_vertice(
            self.vertices, self.faces, ponderar_por_area)

    def matriz_enquadramento(self, F=1.0):
        """S(F/r) T(-c): leva a esfera envolvente para a esfera de
        raio F centrada na origem."""
        s = F / self.raio
        return glm.scale(glm.mat4(1.0), glm.vec3(s)) \
            * glm.translate(glm.mat4(1.0), glm.vec3(*(-self.centro)))

    def suave(self):
        """(dados, indices): posicao e normal de vertice, (V, 6)."""
        dados = np.hstack([self.vertices, self.normais_vertice])
        return dados.astype('f4'), self.faces

    def facetada(self):
        """Dados sem indices: tres vertices proprios por face, todos
        com a normal da face, (3F, 6)."""
        pos = self.vertices[self.faces]                  # (F, 3, 3)
        nor = np.repeat(self.normais_face[:, None], 3, axis=1)
        return np.concatenate([pos, nor], axis=2) \
            .reshape(-1, 6).astype('f4')

    def coordenadas(self, tipo="cilindrico", eixo="y"):
        """(u, v) de cada vertice, pelo mapeamento cilindrico ou
        esferico, com o eixo polar escolhido no papel de y."""
        if eixo not in EIXOS:
            raise ValueError(f"eixo invalido: {eixo}")
        # P relativo ao centro da caixa, com o eixo polar em y.
        p = (self.vertices - self.centro)[:, EIXOS[eixo]]
        px, py, pz = p[:, 0], p[:, 1], p[:, 2]

        # Os dois mapeamentos tem o mesmo u: o angulo em torno do
        # eixo, levado de (-pi, pi] para [0, 1].
        u = np.arctan2(px, pz) / (2.0 * np.pi) + 0.5

        if tipo == "cilindrico":          # altura, de 0 a 1
            v = (py - py.min()) / max(py.max() - py.min(), EPS)
        elif tipo == "esferico":          # elevacao, de 0 a 1
            norma = np.maximum(np.linalg.norm(p, axis=1), EPS)
            phi = np.arcsin(np.clip(py / norma, -1.0, 1.0))
            v = phi / np.pi + 0.5
        else:
            raise ValueError(f"tipo invalido: {tipo}")

        return np.stack([u, v], axis=1).astype('f4')

    def costurar(self, uv):
        """Duplica os vertices da costura.

        Em um triangulo que cruza a costura, os vertices com u < 0,5
        ganham uma copia com u + 1, e o triangulo passa a usar a
        copia. Devolve (uv, faces, origem), em que origem[k] e o
        indice, na malha original, do vertice copiado pela k-esima
        copia.
        """
        faces = self.faces.copy()
        n = len(uv)
        copia = {}               # indice original -> indice da copia
        origem, extras_uv = [], []

        for f, face in enumerate(faces):
            u = uv[face, 0]
            if u.max() - u.min() <= MEIA_VOLTA:
                continue                      # nao cruza a costura
            for k in range(3):
                i = face[k]
                if uv[i, 0] >= MEIA_VOLTA:    # so o lado de u ~ 0
                    continue
                if i not in copia:
                    copia[i] = n + len(origem)
                    origem.append(i)
                    extras_uv.append((uv[i, 0] + 1.0, uv[i, 1]))
                faces[f, k] = copia[i]

        if origem:
            uv = np.vstack([uv, np.array(extras_uv, dtype='f4')])
        return uv, faces, np.array(origem, dtype='u4')

    def texturada(self, tipo="cilindrico", eixo="y", costurar=True):
        """(dados, indices) com 12 floats por vertice: posicao (3),
        normal (3), coordenada de textura (2) e tangente (4).

        Ordem: (u, v), costura, copias de posicao e normal para os
        vertices duplicados e, por ultimo, as tangentes, que usam os
        (u, v) ja costurados.
        """
        uv = self.coordenadas(tipo, eixo)
        vertices, normais = self.vertices, self.normais_vertice

        faces = self.faces
        if costurar:
            uv, faces, origem = self.costurar(uv)
            # As copias herdam a posicao e a normal do original.
            vertices = np.vstack([vertices, vertices[origem]])
            normais = np.vstack([normais, normais[origem]])

        tang = tangentes(vertices, faces, normais, uv)
        dados = np.hstack([vertices, normais, uv, tang]).astype('f4')
        return dados, faces.astype('u4')

    def resumo(self):
        return (f"{self.caminho.name}: {len(self.vertices)} "
                f"vertices, {len(self.faces)} faces, "
                f"raio {self.raio:.4f}")


def normalizar(v):
    comprimento = np.linalg.norm(v, axis=1, keepdims=True)
    return (v / np.maximum(comprimento, EPS)).astype('f4')


def produto_das_arestas(vertices, faces):
    """(A - C) x (B - C) de cada face, sem normalizar: a direcao e
    a da normal, e a norma e o dobro da area."""
    a, b, c = (vertices[faces[:, i]] for i in range(3))
    return np.cross(a - c, b - c)


def normais_de_face(vertices, faces):
    return normalizar(produto_das_arestas(vertices, faces))


def normais_de_vertice(vertices, faces, ponderar_por_area=True):
    """A funcao criar_normais da apostila, sem o laco em Python.

    Sem normalizar as normais das faces, cada face pesa pela sua
    area (tecla A).
    """
    n = produto_das_arestas(vertices, faces)
    if not ponderar_por_area:
        n = normalizar(n)                 # todas com o mesmo peso

    soma = np.zeros_like(vertices)
    # Em soma[faces[:, i]] += n, um indice repetido recebe uma so
    # parcela; np.add.at soma todas.
    for i in range(3):
        np.add.at(soma, faces[:, i], n)
    return normalizar(soma)


def tangentes(vertices, faces, normais, uv):
    """Uma tangente por vertice, com a lateralidade w em .w.

    Por face, resolve o sistema 2x2 que escreve as arestas em
    funcao de t e b; acumula por vertice, ortogonaliza em relacao
    a normal (Gram-Schmidt) e normaliza.
    """
    a, b, c = (vertices[faces[:, i]] for i in range(3))
    ta, tb, tc = (uv[faces[:, i]] for i in range(3))

    e1, e2 = b - a, c - a
    # As mesmas arestas no espaco da textura, uma coluna (F, 1) por
    # componente.
    du1, dv1 = np.split(tb - ta, 2, axis=1)
    du2, dv2 = np.split(tc - ta, 2, axis=1)

    det = du1 * dv2 - du2 * dv1
    # Face degenerada no espaco da textura (det ~ 0): peso zero.
    r = np.zeros_like(det)
    valida = np.abs(det) > EPS
    r[valida] = 1.0 / det[valida]

    t_face = (dv2 * e1 - dv1 * e2) * r
    b_face = (du1 * e2 - du2 * e1) * r

    acc_t = np.zeros_like(vertices, dtype='f8')
    acc_b = np.zeros_like(vertices, dtype='f8')
    for i in range(3):
        np.add.at(acc_t, faces[:, i], t_face)
        np.add.at(acc_b, faces[:, i], b_face)

    # Gram-Schmidt: tira de t a componente na direcao da normal.
    n = normais.astype('f8')
    t = acc_t - n * np.sum(n * acc_t, axis=1, keepdims=True)
    comprimento = np.linalg.norm(t, axis=1, keepdims=True)

    # Vertice sem tangente (t acumulado nulo ou paralelo a n):
    # qualquer vetor perpendicular a n serve. Usamos n x e_k, com
    # e_k o eixo coordenado mais perpendicular a n.
    orfaos = (comprimento < TANGENTE_MIN).ravel()
    if orfaos.any():
        eixo = np.zeros((orfaos.sum(), 3))
        menor = np.argmin(np.abs(n[orfaos]), axis=1)
        eixo[np.arange(orfaos.sum()), menor] = 1.0
        t[orfaos] = np.cross(n[orfaos], eixo)
        comprimento = np.linalg.norm(t, axis=1, keepdims=True)

    t = t / np.maximum(comprimento, EPS)

    # w = -1 onde n x t aponta contra a bitangente acumulada.
    w = np.where(np.sum(np.cross(n, t) * acc_b, axis=1) < 0.0,
                 -1.0, 1.0)
    return np.hstack([t, w[:, None]]).astype('f4')


def ler_off(caminho):
    """Le um OFF de faces triangulares: (vertices, faces)."""
    campos = []
    texto = Path(caminho).read_text(encoding="utf-8")
    for linha in texto.splitlines():
        linha = linha.split("#")[0].strip()
        if linha:
            campos.extend(linha.split())

    if campos[0].upper() != "OFF":
        raise ValueError(f"{caminho}: nao comeca com OFF")

    n_vertices, n_faces = int(campos[1]), int(campos[2])
    p = 4                    # campos[3]: numero de arestas, ignorado

    vertices = np.array(campos[p:p + 3 * n_vertices],
                        dtype='f4').reshape(n_vertices, 3)
    p += 3 * n_vertices

    # Com faces triangulares, cada face ocupa 4 campos: o numero de
    # lados (3) e os tres indices. Lemos todas de uma vez.
    faces = np.array(campos[p:p + 4 * n_faces],
                     dtype='u4').reshape(n_faces, 4)
    if not (faces[:, 0] == 3).all():
        raise ValueError(f"{caminho}: ha faces nao triangulares; "
                         "triangule a malha antes de exportar")

    return vertices, np.ascontiguousarray(faces[:, 1:])