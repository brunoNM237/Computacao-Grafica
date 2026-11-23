"""Trackball virtual, com a orientacao acumulada em um quaternio."""
import glm

ATRITO = 1.5          # desaceleracao da inercia, em rad/s por segundo
VELOCIDADE_MIN = 1e-4


class Trackball:
    def __init__(self, inercia=True):
        self.orientacao = glm.quat(1.0, 0.0, 0.0, 0.0)   # identidade
        self.arrastando = False
        self.ultimo = None
        self.eixo = glm.vec3(0.0, 1.0, 0.0)
        self.velocidade = 0.0
        self.inercia = inercia
        self.largura = self.altura = 1.0

    def redimensionar(self, largura, altura):
        self.largura, self.altura = float(largura), float(altura)

    def _na_esfera(self, x, y):
        """Leva o cursor a esfera unitaria. Fora do circulo, o ponto
        fica na borda (z = 0)."""
        p = glm.vec3(2.0 * x / self.largura - 1.0,
                     1.0 - 2.0 * y / self.altura,
                     0.0)
        quadrado = p.x * p.x + p.y * p.y
        if quadrado >= 1.0:
            p = glm.normalize(p)
        else:
            p.z = glm.sqrt(1.0 - quadrado)
        return p

    def pressionar(self, x, y):
        self.arrastando = True
        self.velocidade = 0.0
        self.ultimo = self._na_esfera(x, y)

    def mover(self, x, y, dt):
        if not self.arrastando or self.ultimo is None:
            return
        atual = self._na_esfera(x, y)
        # |p1 x p2| = sen(theta), que vale ~theta entre dois quadros.
        eixo = glm.cross(self.ultimo, atual)
        angulo = glm.length(eixo)
        if angulo > 1e-9:
            self.eixo = eixo / angulo
            self.orientacao = glm.normalize(
                glm.angleAxis(angulo, self.eixo) * self.orientacao)
            if dt > 1e-6:
                self.velocidade = angulo / dt
        self.ultimo = atual

    def soltar(self):
        self.arrastando = False
        self.ultimo = None
        if not self.inercia:
            self.velocidade = 0.0

    def atualizar(self, dt):
        """Inercia: solto, o objeto continua girando e desacelera."""
        if self.arrastando or self.velocidade <= VELOCIDADE_MIN:
            return
        self.orientacao = glm.normalize(
            glm.angleAxis(self.velocidade * dt, self.eixo)
            * self.orientacao)
        self.velocidade = max(0.0, self.velocidade - ATRITO * dt)

    def zerar(self):
        self.orientacao = glm.quat(1.0, 0.0, 0.0, 0.0)
        self.velocidade = 0.0

    def matriz(self):
        return glm.mat4_cast(self.orientacao)
