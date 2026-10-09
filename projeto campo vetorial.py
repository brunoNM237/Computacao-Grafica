



import sys 

from pathlib import Path
from fisica import calcular_campo, interpolar_cor

import glfw 
import moderngl
import numpy as np
import math

VERMELHO_CARGA = (0.9, 0.2, 0.2, 1.0)
AZUL_CAMPO = (0.2, 0.6, 1.0, 1.0)
FUNDO = (0.08, 0.08, 0.12, 1.0)
AZUL_CARGA = (0.0, 0.0, 0.55, 1.0)


pos_particula_x = 0.0
pos_particula_y = 0.0 
negativo = True

n_linhas = 11
n_colunas = 11



PASSO = 0.05

SHADERS = Path(__file__).parent / "shaders"


def leque(x, y):
    x = np.concatenate(([0.0], x, [x[0]]))
    y = np.concatenate(([0.0], y, [y[0]]))
    return np.column_stack((x, y, np.zeros_like(x), np.ones_like(x))).astype('f4')

def curva_circulo(n=48):
    t = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    return leque(0.8 * np.cos(t), 0.8 * np.sin(t))





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

#criação do grid
def criar_grid(n_linhas=20, n_colunas=20, limite=1.00):

    xs = np.linspace(-limite, limite, n_colunas)
    ys = np.linspace(-limite, limite, n_linhas)
    
    
    
    pontos = []
    for x in xs:
        for y in ys:
            pontos.append((float(x),float(y)))
    return pontos

grid_pontos = criar_grid(n_linhas, n_colunas)
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
    else:
        print(f"Uniform ausente no shader: {nome}")

vbo_circulo, vao_circulo = montar(curva_circulo())
vbo_seta, vao_seta = montar(malha_seta())

def desenhar(vao, escala, deslocamento, cor, modo=moderngl.TRIANGLE_FAN, angulo=0.0):
    ajustar('u_escala', escala)             # escaala
    ajustar('u_deslocamento', deslocamento) # deslocamento
    ajustar('u_cor', cor)                   # cor 
    ajustar('u_angulo', float(angulo))      # angulo
    vao.render(modo)



def tecla(window, key, scancode, action, mods):
    global pos_particula_x
    global pos_particula_y
    global negativo
    global n_linhas
    global n_colunas
    global grid_pontos 
    if action != glfw.PRESS and action != glfw.REPEAT:
        return
    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(window, True)
    elif key in (glfw.KEY_LEFT, glfw.KEY_RIGHT, glfw.KEY_UP, glfw.KEY_DOWN):
        dx = {glfw.KEY_LEFT: -1.0, glfw.KEY_RIGHT: 1.0}.get(key, 0.0)
        dy = {glfw.KEY_DOWN: -1.0, glfw.KEY_UP: 1.0}.get(key, 0.0)
        pos_particula_x = pos_particula_x + dx*PASSO
        pos_particula_y = pos_particula_y + dy*PASSO
    elif key == glfw.KEY_D:
        negativo = not negativo
    elif key == glfw.KEY_U:
        n_linhas = n_linhas + 1
        n_colunas = n_colunas + 1 
        grid_pontos = criar_grid(n_linhas, n_colunas)
    elif key == glfw.KEY_J:
        if n_linhas == 0:
            return 

        n_linhas = n_linhas - 1
        n_colunas = n_colunas - 1 
        grid_pontos = criar_grid(n_linhas, n_colunas)

glfw.set_key_callback(janela, tecla)


while not glfw.window_should_close(janela):
    ajustar('u_atenuacao', 1.0)
    ctx.clear(*FUNDO)

    


    
    if negativo:
        desenhar(vao_circulo, 0.15, (pos_particula_x, pos_particula_y), AZUL_CARGA, modo=moderngl.TRIANGLE_FAN)
    else:
        desenhar(vao_circulo, 0.15, (pos_particula_x, pos_particula_y), VERMELHO_CARGA, modo=moderngl.TRIANGLE_FAN)


    for sx, sy in grid_pontos:
        dist = math.sqrt ((sx - pos_particula_x)**2 + (sy -pos_particula_y)**2)

        
        if dist < 0.15:
                continue
                
        if not negativo: 
            theta, escala , intensidade = calcular_campo(sx, sy, pos_particula_x, pos_particula_y, carga=1.0)
        else:
            theta, escala , intensidade = calcular_campo(sx, sy, pos_particula_x, pos_particula_y, carga=-1.0)
            
            if 0.15 + escala > dist:
                continue

        

        cor_seta = interpolar_cor(intensidade)
        
        
        
        desenhar(vao_seta, escala, (sx, sy), cor_seta, modo=moderngl.LINES, angulo=theta)
    glfw.swap_buffers(janela)
    glfw.poll_events()



for r in (vao_circulo, vao_seta, vbo_circulo, vbo_seta, prog):
    r.release()
glfw.terminate()
print("Execuçao terminada")
