import numpy as np 

def calcular_campo(sx, sy, px, py, carga=1.0):

    dx = sx - px
    dy = sy - py 

    dist2 = dx**2 + dy**2 + 0.005

    intensidade = 0.02 / dist2 


    escala = float(max(0.04, min(intensidade, 0.18)))
    
    if carga > 0:
        angulo = np.arctan2(dy,dx)
    else: 
        angulo = np.arctan2(-dy,-dx)

    return angulo, escala, intensidade





def interpolar_cor(intensidade, int_corte=0.12):
    """
    int_corte: intensidade exata calculada na borda exterior da partícula.
    Quando a seta chega na distância mínima permitida, ela atinge 1.0 (vermelho vivo).
    """
    t = float(np.clip(intensidade / int_corte, 0.0, 1.0))

    if t < 0.33:
        # Longe da partícula: Azul escuro -> Ciano
        k = t / 0.33
        r = 0.1 * (1.0 - k) + 0.0 * k
        g = 0.2 * (1.0 - k) + 0.9 * k
        b = 0.9 * (1.0 - k) + 1.0 * k
    elif t < 0.66:
        # Meia distância: Ciano -> Amarelo/Laranja
        k = (t - 0.33) / 0.33
        r = 0.0 * (1.0 - k) + 1.0 * k
        g = 0.9 * (1.0 - k) + 0.7 * k
        b = 1.0 * (1.0 - k) + 0.1 * k
    else:
        # No limite da carga: Laranja -> Vermelho puro (1.0, 0.0, 0.0)
        k = (t - 0.66) / 0.34
        r = 1.0
        g = 0.7 * (1.0 - k) + 0.0 * k
        b = 0.1 * (1.0 - k) + 0.0 * k

    return (float(r), float(g), float(b), 1.0)