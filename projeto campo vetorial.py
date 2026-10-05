



import sys 

from pathlib import Path


import glfw 
import moderngl
import numpy as np

VERMELHO_CARGA = (0.9, 0.2, 0.2, 1.0)
AZUL_CAMPO = (0.2, 0.6, 1.0, 1.0)
FUNDO = (0.08, 0.08, 0.12, 1.0)


pos_particula_x = 0.1 
pos_particula_y = 0.3 


pos_seta_x = 0.35
pos_seta_y = 0.20


PASSO = 0.05

SHADERS = Path(__file__).parent / "shaders"


def leque(x, y):
    x = np.concatenate(([0.0], x, [x[0]]))
    y = np.concatenate(([0.0], y, [y[0]]))
    return np.column_stack((x, y, np.zeros_like(x), np.ones_like(x))).astype('f4')

def curva_circulo(n=48):
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return leque(np.cos(t), np.sin(t))

def malha_seta():
    segmentos = [
        # Haste
        0.0,  0.0, 0.0, 1.0,
        1.0,  0.0, 0.0, 1.0,
        # Farpa superior
        1.0,  0.0, 0.0, 1.0,
        0.75, 0.15, 0.0, 1.0,
        # Farpa inferior
        1.0,  0.0, 0.0, 1.0,
        0.75, -0.15, 0.0, 1.0,
    ]
    return np.array(segmentos, dtype='f4')


def erro_glfw(codigo, descricao):
    """Substitui o aviso padrão do pyGLFW: imprime código 
    e descrição de qualquer erro do GLFW em stderr"""
    print(f"GLFW [{codigo}]: {descricao}", file=sys.stderr)

glfw.set_error_callback(erro_glfw)


if not glfw.init():
    sys.exit("FALHA: glfw nao inicializou")

glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)


janela = glfw.create_window(600, 600, "Troca de Diagonal", None, None)
if not janela:
    glfw.terminate()
    sys.exit("FALHA: nao foi possivel criar a janela")


glfw.make_context_current(janela)
glfw.swap_interval(1)
ctx = moderngl.create_context()


prog = ctx.program(
    vertex_shader=(SHADERS / "senhor_coracao.vert").read_text(encoding="utf-8"),
    fragment_shader=(SHADERS / "senhor_coracao.frag").read_text(encoding="utf-8"),
)



def montar(vertices):
    vbo = ctx.buffer(vertices.tobytes())
    return vbo, ctx.vertex_array(prog, [(vbo, '4f', 'vPosition')])

def ajustar(nome, valor):
    u = prog.get(nome, None)
    if u is not None:
        u.value = valor

vbo_circulo, vao_circulo = montar(curva_circulo())
vbo_seta, vao_seta = montar(malha_seta())

def desenhar(vao, escala, deslocamento, cor, modo=moderngl.TRIANGLE_FAN, angulo=0.0):
    ajustar('u_escala', escala)             # Define o tamanho na GPU
    ajustar('u_deslocamento', deslocamento) # Define a posição (x, y) na GPU
    ajustar('u_cor', cor)                   # Define a cor (RGBA) na GPU
    ajustar('u_angulo', float(angulo))
    vao.render(modo)



def tecla(window, key, scancode, action, mods):
    global pos_particula_x
    global pos_particula_y

    if action != glfw.PRESS and action != glfw.REPEAT:
        return
    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(window, True)
    elif key in (glfw.KEY_LEFT, glfw.KEY_RIGHT, glfw.KEY_UP, glfw.KEY_DOWN):
        dx = {glfw.KEY_LEFT: -1.0, glfw.KEY_RIGHT: 1.0}.get(key, 0.0)
        dy = {glfw.KEY_DOWN: -1.0, glfw.KEY_UP: 1.0}.get(key, 0.0)
        pos_particula_x = pos_particula_x + dx*PASSO
        pos_particula_y = pos_particula_y + dy*PASSO

glfw.set_key_callback(janela, tecla)


while not glfw.window_should_close(janela):
    ajustar('u_atenuacao', 1.0)
    ctx.clear(*FUNDO)

    dx = pos_seta_x - pos_particula_x
    dy = pos_seta_y - pos_particula_y


    angulo = np.arctan2(dy, dx)
    # Círculo (ex: partícula/carga) no centro (0.0, 0.0) com escala 0.15

    # Seta (vetor de campo) saindo de (0.2, 0.0) com tamanho 0.3
    

    desenhar(vao_circulo, 0.12, (pos_particula_x, pos_particula_y), VERMELHO_CARGA, modo=moderngl.TRIANGLE_FAN)

    desenhar(vao_seta, 0.25, (pos_seta_x, pos_seta_y), AZUL_CAMPO, modo=moderngl.LINES, angulo=angulo)


    glfw.swap_buffers(janela)
    glfw.poll_events()


for r in (vao_circulo, vao_seta, vbo_circulo, vbo_seta, prog):
    r.release()
glfw.terminate()
print("Execucao finalizada.")