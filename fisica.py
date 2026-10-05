import numpy as np 

def calcular_campo(sx, sy, px, py, carga=1.0):

    dx = sx - px
    dy = sy - py 

    dist2 = dx**2 + dy**2 + 0.005

    intensidade = 0.02 / dist2 


    escala = float(np.clip(intensidade, 0.04, 0.18))  

    if carga > 0:
        angulo = np.arctan2(dy,dx)
    else: 
        angulo = np.arctan2(-dy,-dx)

    return angulo, escala, intensidade



def interpolar_cor(intensidade, t_max=0.25):
    """
    Gradiente de campo elétrico em 2 etapas:
    t in [0.0, 0.5]: Azul escuro (0.1, 0.2, 0.9) -> Ciano brilhante (0.0, 0.9, 1.0)
    t in [0.5, 1.0]: Ciano brilhante -> Amarelo/Laranja de alta energia (1.0, 0.85, 0.1)
    """
    t = float(np.clip(intensidade / t_max, 0.0, 1.0))

    if t < 0.5:
        # Normaliza o primeiro trecho para [0, 1]
        k = t / 0.5
        r = 0.1 * (1.0 - k) + 0.0 * k
        g = 0.2 * (1.0 - k) + 0.9 * k
        b = 0.9 * (1.0 - k) + 1.0 * k
    else:
        # Normaliza o segundo trecho para [0, 1]
        k = (t - 0.5) / 0.5
        r = 0.0 * (1.0 - k) + 1.0 * k
        g = 0.9 * (1.0 - k) + 0.85 * k
        b = 1.0 * (1.0 - k) + 0.1 * k

    return (float(r), float(g), float(b), 1.0)