
import sys
from linkedList import LinkedList
from pathlib import Path

import glfw
import moderngl
import numpy as np
import random 


## CONFIGURAÇÃO

SHADERS = Path(__file__).parent / "shaders"


PLACAR_CANTO = [-0.8,0.8]
PLACAR_PASSO = 0.06
ESCALA_MARCA = 0.15
SCORE = 0 

DIRECAO = "cima"
VELOCIDADE = 1 
ESTADO = "game_on"
INTERVALO_MOVIMENTO = 0.15

vsync = True
tempo_acumulado = 0.0


n_linhas = 8
n_colunas = 8


quadrado_length = 0.2
quadrado_length = 2 / n_linhas
metade = quadrado_length / 2 

COR_COBRA = (random.random(), random.random(), random.random(), 1.0)
VERMELHO_COMIDA = (0.8, 0.0, 0.0, 1.0)






### ESTADO DO JOGO


tabuleiro = [
    [0 for _ in range(n_colunas)]
    for _ in range(n_linhas)
]




cobra = LinkedList()
cobra.add([3,3])
cobra.add([3,4])
cobra.add([3,5])

tabuleiro[3][3] = 1 
tabuleiro[3][4] = 1
tabuleiro[3][5] = 1 

### GLFW 
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


janela = glfw.create_window(600, 800, "Quadrado com EBO", None, None)
if not janela:
    glfw.terminate()
    sys.exit("FALHA: nao foi possivel criar a janela")

glfw.make_context_current(janela)
ctx = moderngl.create_context()


### SHADERS E GEOMETRIA 
prog = ctx.program(
    vertex_shader=(SHADERS / "basico.vert").read_text(encoding="utf-8"),
    fragment_shader=(SHADERS / "basico.frag").read_text(encoding="utf-8"),
)
vertices_quadrado = np.array([
    -metade, -metade, 0.0, 1.0,      
     metade, -metade, 0.0, 1.0,  
     metade,  metade, 0.0, 1.0,     
    -metade,  metade, 0.0, 1.0
], dtype='f4')


indices_triangulos = np.array([0, 1, 2, 0, 2, 3], dtype='u4')

indices_borda = np.array([0, 1, 2, 3], dtype='u4')

vbo = ctx.buffer(vertices_quadrado.tobytes())


ebo_triangulos = ctx.buffer(indices_triangulos.tobytes())
ebo_borda = ctx.buffer(indices_borda.tobytes())



vao_triangulos = ctx.vertex_array(
    prog, [(vbo, '4f', 'vPosition')], index_buffer=ebo_triangulos
)

vao_borda = ctx.vertex_array(
    prog, [(vbo, '4f', 'vPosition')], index_buffer=ebo_borda

)



def ajustar(nome, valor): 
    u = prog.get(nome, None)
    if u is not None:
        u.value = valor 
    else: 
        print(f"Uniform ausente no shader: {nome}")                    

def desenhar(vao, deslocamento, cor, modo=moderngl.TRIANGLES, escala=1.0):

    ajustar('u_deslocamento', deslocamento)
    ajustar('u_cor', cor)
    ajustar('u_escala', escala)
    
    vao.render(modo)
## CRIAÇÂO DO GRID

def criar_grid(n_linhas, n_colunas, quadrado_length,limite=1.00): 
    

    pontos = []
    largura = 2 / n_colunas
    altura = 2 / n_linhas
    
    for i in range(n_linhas):
        for j in range (n_colunas):
            x = -1 + i * largura + largura / 2  
            y = -1 + j *  altura + altura / 2   

            pontos.append( (x,y))
    return pontos 


grid_pontos = criar_grid (n_linhas, n_colunas, quadrado_length)  



## COORDENADA DA COMIDA E RENDERIZAÇÃO

def gerar_comida(): 
        linha = random.randrange(n_linhas)
        coluna = random.randrange(n_colunas -1)
    
        while tabuleiro[linha][coluna] != 0:
            linha = random.randrange(n_linhas)
            coluna = random.randrange(n_colunas -1 ) 
    
        
    
        
        return [linha, coluna]
coordenada_comida = gerar_comida()
print(coordenada_comida)

def desenhar_grid():
     y_ignorar = grid_pontos[7][1]
     
     
     for sx, sy in grid_pontos: 
            if sy == y_ignorar:
                continue
            desenhar(vao_triangulos, (sx, sy), (0.0, 0.0, 0.0, 1.0), modo=moderngl.TRIANGLES)
            desenhar(vao_borda, (sx, sy), (1.0, 1.0, 1.0, 1.0) ,modo=moderngl.LINE_LOOP)

def desenhar_cobra():
    for coordinate in cobra:   
            linha = coordinate[0]
            coluna = coordinate[1]

            indice = n_linhas*linha + coluna
            x, y = grid_pontos[indice]
            if (coluna != n_linhas - 1): 
                desenhar(vao_triangulos, (x, y), COR_COBRA, modo=moderngl.TRIANGLES)

def desenhar_comida(coordenada_comida): 
    linha, coluna = coordenada_comida
    indice = linha * n_colunas + coluna
    x, y = grid_pontos[indice]
    desenhar(vao_triangulos, (x, y), VERMELHO_COMIDA, modo=moderngl.TRIANGLES)

def desenhar_placar(pontuacao):
    for i in range(pontuacao):
        x = PLACAR_CANTO[0] + i * PLACAR_PASSO
        y = PLACAR_CANTO[1]

        desenhar(
            vao_triangulos,
            (x, y),
            COR_COBRA,
            escala=ESCALA_MARCA
        )
### Lógica do jogo`

def mover_cobra():
    global ESTADO
    global coordenada_comida
    global SCORE 
    
    linha, coluna = cobra.head.get_data()
    match DIRECAO:
        case "cima":
            nova_posicao = [linha, coluna + 1]
        case "baixo":
            nova_posicao = [linha, coluna - 1]
        case "esquerda": 
            nova_posicao = [linha - 1, coluna]
        case "direita": 
            nova_posicao = [linha + 1, coluna]
    
    linha, coluna = nova_posicao
    if (linha < 0 or linha >= n_linhas or 
        coluna < 0 or coluna >= n_colunas -1):
        ESTADO = "game_over"
        return

    for segmento in cobra:
        if nova_posicao == segmento:
            ESTADO = "game_over"
            break

    cobra.add(nova_posicao)
    linha, coluna = nova_posicao
    tabuleiro[linha][coluna] = 1
    if nova_posicao == coordenada_comida:
        
        coordenada_comida = gerar_comida()
        SCORE = SCORE + 1
    else: 
        tail = cobra.remove_last()
        linha, coluna = tail
        tabuleiro[linha][coluna] = 0

    
    
    
   
   

    

    







def tecla(window, key, scancode, action, mods):
    global DIRECAO
    global cobra
    global ESTADO
    global INTERVALO_MOVIMENTO
    global VSYNC
    global nova_direcao
    global SCORE

    if action != glfw.PRESS and action != glfw.REPEAT:
        return

    if key == glfw.KEY_ESCAPE:
        glfw.set_window_should_close(window, True)

    # Direction
    oposta = {
    "cima": "baixo",
    "baixo": "cima",
    "esquerda": "direita",
    "direita": "esquerda"
    }
    
    match key:
        case glfw.KEY_LEFT:
            nova_direcao = "esquerda"

        case glfw.KEY_RIGHT:
            nova_direcao = "direita"

        case glfw.KEY_UP:
            nova_direcao = "cima"

        case glfw.KEY_DOWN:
            nova_direcao = "baixo"
    if DIRECAO is not None and nova_direcao != oposta[DIRECAO]:
        DIRECAO = nova_direcao
    
    # Restart
    if key == glfw.KEY_R:
        cobra = LinkedList()

        cobra.add([3, 3])
        cobra.add([3, 4])
        cobra.add([3, 5])

        ESTADO = "game_on"
        DIRECAO = "cima"
        SCORE = 0
    # Pause / Resume
    if key == glfw.KEY_P:
        if ESTADO == "game_on":
            ESTADO = "pausado"

        elif ESTADO == "pausado":
            ESTADO = "game_on"

    #Velocidade da cobra
    if key == glfw.KEY_I:
        INTERVALO_MOVIMENTO -= 0.01

    if key == glfw.KEY_O:
        INTERVALO_MOVIMENTO += 0.01

    # VSync
    if key == glfw.KEY_V:
        VSYNC = not VSYNC
        glfw.swap_interval(1 if VSYNC else 0)


glfw.set_key_callback(janela, tecla)

instante_anterior = glfw.get_time() 
quadros, marco = 0, instante_anterior
tempo_acumulado = 0



glfw.set_key_callback(janela, tecla)
while not glfw.window_should_close(janela):
    
    agora = glfw.get_time()
    dt = agora - instante_anterior
    instante_anterior = agora 

    quadros += 1 
    if agora - marco >= 0.5:
        glfw.set_window_title(
        janela,
        f"VSync {'ON' if vsync else 'OFF'} - "
        f"{quadros / (agora - marco):6.1f} FPS"
        )
        quadros , marco = 0 , agora

    #update
    if ESTADO == "game_on":
        tempo_acumulado += dt

        if tempo_acumulado >= INTERVALO_MOVIMENTO:
            tempo_acumulado -= INTERVALO_MOVIMENTO
            mover_cobra()
            COR_COBRA = (random.random(), random.random(), random.random(), 1.0)

    
    #renderizacao
    ctx.clear(0.0, 0.0, 0.0, 1.0)

    desenhar_grid()
    desenhar_comida(coordenada_comida)
    desenhar_cobra()
    desenhar_placar(SCORE)
    if ESTADO == "game_over":
        pass    
    
    
    
    
   
        
    
    
    glfw.swap_buffers(janela) 
    glfw.poll_events()
    if ESTADO == "pausado":
        continue
vao.release()
ebo.release()
vbo.release()
prog.release()
glfw.terminate()
print("Execucao finalizada.")
