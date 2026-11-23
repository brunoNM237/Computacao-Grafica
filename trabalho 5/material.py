"""Materiais e luz do modelo de Phong.

Os coeficientes estao em luz linear: a codificacao sRGB da saida
e feita pelo OpenGL (GL_FRAMEBUFFER_SRGB).
"""
import glm


class Material:
    def __init__(self, nome, ka, kd, ks, alfa):
        self.nome = nome
        self.ka, self.kd, self.ks = glm.vec3(*ka), glm.vec3(*kd), \
            glm.vec3(*ks)
        self.alfa = alfa


# Tecla M. Cada valor e a cor que se quer ver na tela (sRGB),
# decodificada uma vez, aqui, pela equacao do sRGB.
MATERIAIS = [
    Material("zumbi", (0.005, 0.09, 0.05),
             (0.18, 0.32, 0.15), (0.12, 0.16, 0.12), 16.0),
    Material("aco", (0.08, 0.08, 0.11),
             (0.28, 0.31, 0.36), (0.80, 0.84, 0.90), 128.0),
    Material("gesso", (0.010, 0.010, 0.010),
             (0.477, 0.448, 0.393), (0.002, 0.002, 0.002), 4.0),
]

# Materiais fixos dos modos de textura; os demais usam a tecla M.
# Valores escolhidos direto em luz linear.
#
# TEXTURA (modos 8, 9 e =): a imagem faz o papel de kd, e o kd
# daqui nao e lido (textura.frag nao tem u_kd).
#
# MAPA_NORMAIS (modo 0): a normal vem da imagem de normais (tecla
# T troca o par). Daqui saem ka, ks e alfa e, com o albedo
# desligado (tecla X), um kd cinza claro no lugar da imagem de cor.
TEXTURA = Material("textura", (0.05, 0.05, 0.06), (1.0, 1.0, 1.0),
                   (0.25, 0.25, 0.25), 48.0)
MAPA_NORMAIS = Material("mapa de normais", (0.06, 0.05, 0.05),
                        (0.62, 0.58, 0.54), (0.30, 0.30, 0.30),
                        48.0)

class Luz:
    def __init__(self):
        # w = 1: pontual; w = 0: direcional (tecla L)
        self.posicao = glm.vec4(1.6, 1.4, 2.4, 1.0)
        self.ia = glm.vec3(1.0, 1.0, 1.0)
        self.id = glm.vec3(1.0, 1.0, 1.0)
        self.is_ = glm.vec3(1.0, 1.0, 1.0)

    def alternar_tipo(self):
        self.posicao.w = 0.0 if self.posicao.w == 1.0 else 1.0
