"""
Senhor Coracao: uma geometria desenhada varias vezes.

Duas curvas na VRAM (o coracao e um circulo) e cinco desenhos por quadro. O que
muda de um desenho para o outro nao esta em nenhum VBO: esta em variaveis
uniformes. As teclas nao animam nada -- elas trocam o valor de uma uniforme, e
o desenho seguinte ja sai diferente.

MCCC007-23 - Computacao Grafica - UFABC

Executar: python 06_senhor_coracao.py
Teclas:   SETAS movem o olhar | D alterna dia/noite | ESC sai
"""
import sys
from pathlib import Path

import glfw
import moderngl
import numpy as np

SHADERS = Path(__file__).parent / "shaders"

MAGENTA = (0.85, 0.10, 0.45, 1.0)
BRANCO_OLHO = (1.0, 1.0, 1.0, 1.0)
PRETO = (0.05, 0.05, 0.05, 1.0)
FUNDO_DIA = (0.96, 0.96, 0.94, 1.0)
FUNDO_NOITE = (0.05, 0.05, 0.12, 1.0)

ESCALA_CORPO = 0.62
ESCALA_OLHO, ESCALA_PUPILA = 0.085, 0.040
CENTRO_OLHO = (0.17, 0.20)   # afastamento do eixo e altura de cada olho

# Ate onde a pupila pode sair do centro do olho, sem escapar do branco.
LIMITE_OLHAR = ESCALA_OLHO - ESCALA_PUPILA
PASSO_OLHAR = LIMITE_OLHAR / 2.0


def leque(x, y):
    """Empacota uma curva fechada como TRIANGLE_FAN: primeiro o centro, depois
    a curva, e o primeiro ponto repetido no fim para fechar a volta."""
    x = np.concatenate(([0.0], x, [x[0]]))
    y = np.concatenate(([0.0], y, [y[0]]))
    return np.column_stack((x, y, np.zeros_like(x), np.ones_like(x))).astype('f4')


def curva_coracao(n=180):
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    x = 16.0 * np.sin(t) ** 3
    y = (13.0 * np.cos(t) - 5.0 * np.cos(2 * t)
         - 2.0 * np.cos(3 * t) - np.cos(4 * t))
    y = y - 0.5 * (y.max() + y.min())      # centra a curva na origem
    return leque(x / 17.0, y / 17.0)       # normaliza para caber em [-1, 1]


def curva_circulo(n=48):
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return leque(np.cos(t), np.sin(t))


def erro_glfw(codigo, descricao):
    """Substitui o aviso padrão do pyGLFW: imprime código 
    e descrição de qualquer erro do GLFW em stderr"""
    print(f"GLFW [{codigo}]: {descricao}", file=sys.stderr)


glfw.set_error_callback(erro_glfw)   # antes de glfw.init(), de proposito

if not glfw.init():
    sys.exit("FALHA: glfw nao inicializou")

glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
# Sem a dica acima, o macOS recusa qualquer contexto 3.2+ e
# create_window devolve None. E inofensiva no Windows e no Linux.
glfw.window_hint(glfw.SAMPLES, 4)        # quatro amostras por pixel
glfw.window_hint(glfw.RESIZABLE, False)  # janela quadrada: ver a nota

janela = glfw.create_window(640, 640, "Senhor Coracao", None, None)
if not janela:
    glfw.terminate()
    sys.exit("FALHA: nao foi possivel criar a janela")

glfw.make_context_current(janela)
ctx = moderngl.create_context()

# SAMPLES e uma dica, nao uma garantia: o driver pode entregar menos amostras
# do que se pediu. Conferir e barato.
print(f"amostras por pixel obtidas: {ctx.screen.samples}")

prog = ctx.program(
    vertex_shader=(SHADERS / "senhor_coracao.vert").read_text(encoding="utf-8"),
    fragment_shader=(SHADERS / "senhor_coracao.frag").read_text(encoding="utf-8"),
)


def montar(vertices):
    vbo = ctx.buffer(vertices.tobytes())
    return vbo, ctx.vertex_array(prog, [(vbo, '4f', 'vPosition')])


vbo_coracao, vao_coracao = montar(curva_coracao())
vbo_circulo, vao_circulo = montar(curva_circulo())

# Todo o estado do programa cabe em dois numeros e um booleano.
olhar_x, olhar_y = 0.0, 0.0
noite = False


def tecla(window, key, scancode, action, mods):
    global olhar_x, olhar_y, noite
    if action != glfw.PRESS and action != glfw.REPEAT:
        return
    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(window, True)
    elif key == glfw.KEY_D:
        noite = not noite
    elif key in (glfw.KEY_LEFT, glfw.KEY_RIGHT, glfw.KEY_UP, glfw.KEY_DOWN):
        dx = {glfw.KEY_LEFT: -1.0, glfw.KEY_RIGHT: 1.0}.get(key, 0.0)
        dy = {glfw.KEY_DOWN: -1.0, glfw.KEY_UP: 1.0}.get(key, 0.0)
        olhar_x += dx * PASSO_OLHAR
        olhar_y += dy * PASSO_OLHAR
        # O branco do olho e um CIRCULO, entao o limite tem de ser no vetor.
        # Limitar cada eixo em separado prende a pupila num quadrado, e na
        # diagonal ela escapa: o centro chega a 0.064 do centro do olho e a
        # borda da pupila a 0.104, contra um raio de 0.085.
        distancia = (olhar_x ** 2 + olhar_y ** 2) ** 0.5
        if distancia > LIMITE_OLHAR:
            olhar_x *= LIMITE_OLHAR / distancia
            olhar_y *= LIMITE_OLHAR / distancia


glfw.set_key_callback(janela, tecla)


def ajustar(nome, valor):
    """Escreve num uniforme, se ele existir.

    Um uniforme que o shader deixa de usar e descartado pelo ligador do
    GLSL, e prog[nome] levantaria KeyError. Os experimentos do capitulo
    fazem exatamente isso -- ignorar u_cor, ignorar u_atenuacao -- entao
    o acesso passa todo por aqui.
    """
    uniforme = prog.get(nome, None)
    if uniforme is not None:
        uniforme.value = valor


def desenhar(vao, escala, deslocamento, cor):
    """Carrega os tres uniformes daquele desenho e dispara a chamada."""
    ajustar('u_escala', escala)
    ajustar('u_deslocamento', deslocamento)
    ajustar('u_cor', cor)
    vao.render(moderngl.TRIANGLE_FAN)


while not glfw.window_should_close(janela):
    # Uma escrita por quadro: os cinco desenhos abaixo leem este mesmo valor.
    ajustar('u_atenuacao', 0.35 if noite else 1.0)

    ctx.clear(*(FUNDO_NOITE if noite else FUNDO_DIA))

    desenhar(vao_coracao, ESCALA_CORPO, (0.0, 0.0), MAGENTA)

    # A mesma geometria de circulo, quatro vezes, so mudando os uniformes.
    for lado in (-1.0, 1.0):
        centro = (lado * CENTRO_OLHO[0], CENTRO_OLHO[1])
        desenhar(vao_circulo, ESCALA_OLHO, centro, BRANCO_OLHO)
        desenhar(vao_circulo, ESCALA_PUPILA,
                 (centro[0] + olhar_x, centro[1] + olhar_y), PRETO)

    glfw.swap_buffers(janela)
    glfw.poll_events()

for recurso in (vao_coracao, vao_circulo, vbo_coracao, vbo_circulo, prog):
    recurso.release()
glfw.terminate()
print("Execucao finalizada.")
