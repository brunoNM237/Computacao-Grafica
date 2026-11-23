"""Camera LookAt e as projecoes perspectiva e ortografica."""
import glm

FOVY = 45.0          # abertura vertical, em graus
 
# malha.matriz_enquadramento() coloca o modelo dentro de uma esfera de
# raio 1 centrada na origem. 
# O trackball so gira o modelo.
#  Os planos near e far ficam a RAIO + MARGEM do centro: envolvem a
# esfera inteira, com o near o mais longe possivel da camera.
RAIO_MODELO = 1.0
MARGEM = 0.05
NEAR_MIN = 0.05      # se a camera chegar perto demais do modelo


class Camera:
    def __init__(self, distancia=3.0):
        self.distancia = distancia
        self.centro = glm.vec3(0.0, 0.0, 0.0)
        self.cima = glm.vec3(0.0, 1.0, 0.0)
        self.aspecto = 1.0
        self.fovy = glm.radians(FOVY)
        self.perspectiva = True

    @property
    def olho(self):
        return self.centro + glm.vec3(0.0, 0.0, self.distancia)

    @property
    def near(self):
        return max(NEAR_MIN, self.distancia - RAIO_MODELO - MARGEM)

    @property
    def far(self):
        return self.distancia + RAIO_MODELO + MARGEM
  
    def visao(self):
        return glm.lookAt(self.olho, self.centro, self.cima)

    def projecao(self):
        if self.perspectiva:
            return glm.perspective(self.fovy, self.aspecto,
                                   self.near, self.far)
        # Na ortografica, o tamanho na tela nao depende da distancia.
        # Usamos a meia-altura da perspectiva no plano do centro,
        # t = d tan(fovy/2): o modelo nao muda de tamanho ao trocar
        # de projecao, e a roda do mouse continua aproximando.
        t = self.distancia * glm.tan(self.fovy / 2.0)
        r = t * self.aspecto
        return glm.ortho(-r, r, -t, t, self.near, self.far)