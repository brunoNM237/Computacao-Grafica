"""
Cavaleiro vs Zumbis
Baseado no Visualizador v3.

Controles:
  A / D ou Setas : mover o cavaleiro
  ESPACO         : golpe de espada
  R              : reiniciar apos Game Over
  Q              : alternar Camera Lateral / Camera Orbital (mouse + scroll)
  B / T / L      : Blinn-Phong / Cartoon / Luz pontual
  W / C / Z      : aramado / descarte de faces / zerar Trackball
  ESC            : sair
"""
import math
import random
import sys
from pathlib import Path

import glfw
import glm
import moderngl
import numpy as np

import camera as mod_camera
import texturas as tx
from geometria import criar_cubo
from malha import Malha
from material import MATERIAIS, Luz
from trackball import Trackball

AQUI = Path(__file__).parent
PASTA_TEXTURAS = AQUI / "texturas"
LARGURA, ALTURA = 900, 600
FUNDO = (0.08, 0.09, 0.11)
ZOOM_MIN, ZOOM_MAX = 4.0, 22.0
NEAR, FAR = 0.5, 60.0
DIST_CAM1 = 9.0
NIVEIS_CARTOON = 10
PASSO_ZOOM = 0.5
GL_FRAMEBUFFER_SRGB = 0x8DB9
DT_MAXIMO = 0.05

LIMITE_X = 4.5
SPAWN_X = 5.8
VEL_CAV = 4.5
VEL_ZUMBI_INI = 1.8
PASSO_VEL = 0.35           # quanto o zumbi acelera a cada spawn
MEIO_BONECO = 0.45         # meia-largura do cavaleiro e do zumbi
MEIO_ESPADA = 0.70         # meia-largura da area do golpe
DURACAO_GOLPE = 0.25

CAMPOS_CUBO = [('3f', 'vPosition'), ('3f', 'vNormal'), ('2f', 'vTexCoord')]
CAMPOS_TEXTURA = CAMPOS_CUBO + [('4f', 'vTangente')]


def colidiu(x1, meio1, x2, meio2):
    """Sobreposicao em X: centros distam menos que a soma das meias-larguras."""
    return abs(x1 - x2) < meio1 + meio2


estado = {
    "aramado": False, "blinn": True, "cartoon": False,
    "luz_pontual": True, "cam_orbital": False,
    "tempo": 0.0, "descarte": True,
}


def reiniciar():
    estado.update({
        "cav_x": 0.0, "cav_dir": 1.0, "golpe": 0.0,
        "zumbi_x": random.choice([-SPAWN_X, SPAWN_X]),
        "zumbi_vel": VEL_ZUMBI_INI,
        "pontos": 0, "game_over": False,
    })


reiniciar()


def erro_glfw(codigo, descricao):
    print(f"GLFW [{codigo}]: {descricao}", file=sys.stderr)


def matriz_normal(modelo):
    """Inversa transposta do bloco 3x3 da matriz de modelo."""
    return glm.transpose(glm.inverse(glm.mat3(modelo)))


def carregar_programa(ctx, nome):
    return ctx.program(
        vertex_shader=(AQUI / "shaders" / f"{nome}.vert")
        .read_text(encoding="utf-8"),
        fragment_shader=(AQUI / "shaders" / f"{nome}.frag")
        .read_text(encoding="utf-8"))


def vao_de(ctx, prog, vbo, ebo=None, campos=CAMPOS_CUBO):
    formato, nomes = [], []
    for tamanho, nome in campos:
        if nome in prog:
            formato.append(tamanho)
            nomes.append(nome)
        else:
            formato.append(f"{tamanho[0]}x4")
    return ctx.vertex_array(prog, [(vbo, " ".join(formato), *nomes)],
                            index_buffer=ebo)


def enviar(prog, **uniformes):
    for nome, valor in uniformes.items():
        if nome not in prog:
            continue
        if isinstance(valor, (glm.mat3, glm.mat4)):
            prog[nome].write(valor.to_bytes())
        else:
            prog[nome].value = valor


def abrir(nome):
    caminho = PASTA_TEXTURAS / nome
    if not caminho.exists():
        sys.exit(f"FALHA: imagem nao encontrada: {caminho}")
    return tx.ler(caminho)


class MalhaGPU:
    def __init__(self, ctx, prog, dados, indices,
                 campos=CAMPOS_CUBO, enquadramento=None):
        self.vbo = ctx.buffer(dados.tobytes())
        self.ebo = ctx.buffer(indices.tobytes())
        self.vao = vao_de(ctx, prog, self.vbo, self.ebo, campos)
        self.enquadramento = (enquadramento if enquadramento is not None
                              else glm.mat4(1.0))

    @classmethod
    def de_off(cls, ctx, prog, caminho):
        malha = Malha(caminho)
        dados, indices = malha.texturada("cilindrico", "y", costurar=True)
        print(malha.resumo())
        return cls(ctx, prog, dados, indices,
                   campos=CAMPOS_TEXTURA,
                   enquadramento=malha.matriz_enquadramento(F=1.0))

    def desenhar(self):
        self.vao.render(moderngl.TRIANGLES)

    def liberar(self):
        for r in (self.vao, self.ebo, self.vbo):
            r.release()


def desenhar_quadro(ctx, prog, objetos, texs, luz_dir, luz_pont,
                    estado, camera, bola):
    # 1. Pipeline sRGB e estados do OpenGL
    ctx.disable_direct(GL_FRAMEBUFFER_SRGB)
    ctx.clear(*FUNDO, depth=1.0)
    ctx.enable_direct(GL_FRAMEBUFFER_SRGB)

    if estado["descarte"]:
        ctx.enable(moderngl.CULL_FACE)
    else:
        ctx.disable(moderngl.CULL_FACE)
    ctx.wireframe = estado["aramado"]

    # 2. Cameras (projecao com NEAR e FAR justificados)
    pos_cav = glm.vec3(estado["cav_x"], 1.0, 0.0)
    projecao = glm.perspective(glm.radians(45.0), camera.aspecto, NEAR, FAR)

    if estado["cam_orbital"]:
        # Camera 2: Orbital (Trackball + scroll)
        giro = bola.matriz()
        visao = camera.visao()
        olho = camera.olho
    else:
        # Camera 1: LookAt lateral seguindo o cavaleiro
        giro = glm.mat4(1.0)
        olho = glm.vec3(pos_cav.x, pos_cav.y + 1.8, DIST_CAM1)
        visao = glm.lookAt(olho, pos_cav + glm.vec3(0, 0.4, 0), glm.vec3(0, 1, 0))

    f = float(estado["luz_pontual"])

    enviar(prog,
           u_visao=visao, u_projecao=projecao, u_olho=olho,
           u_base=0, u_usar_textura=True,
           u_blinn=estado["blinn"], u_cartoon=estado["cartoon"], u_niveis=NIVEIS_CARTOON,
           u_luz_dir=luz_dir.posicao,
           u_ia_dir=luz_dir.ia, u_id_dir=luz_dir.id, u_is_dir=luz_dir.is_,
           u_luz_pont=giro * glm.vec4(pos_cav + glm.vec3(0, 1.2, 0.8), 1.0),
           u_ia_pont=luz_pont.ia * f, u_id_pont=luz_pont.id * f, u_is_pont=luz_pont.is_ * f)

    # 3. Hierarquia do cavaleiro + espada
    M_cav = glm.rotate(glm.translate(giro, pos_cav),
                       estado["cav_dir"] * math.pi * 0.5, glm.vec3(0, 1, 0))
    if estado["game_over"]:
        M_cav = glm.rotate(M_cav, -math.pi * 0.5, glm.vec3(1, 0, 0))

    ang_espada = 1.4 if estado["golpe"] > 0.0 else 0.2
    M_ombro = glm.rotate(glm.translate(M_cav, glm.vec3(-0.45, 0.0, 0.15)),
                         ang_espada, glm.vec3(1, 0, 0))
    M_espada = glm.scale(glm.translate(M_ombro, glm.vec3(0.0, 0.45, 0.20)),
                         glm.vec3(0.10, 0.90, 0.06))

    # 4. Hierarquia do zumbi + 2 bracos (um sobe, outro desce)
    sentido_z = 1.0 if estado["cav_x"] > estado["zumbi_x"] else -1.0
    M_zum = glm.rotate(glm.translate(giro, glm.vec3(estado["zumbi_x"], 1.0, 0.0)),
                       sentido_z * math.pi * 0.5, glm.vec3(0, 1, 0))
    osc = 0.6 * math.sin(estado["tempo"] * 6.0)
    M_braco_dir = glm.scale(
        glm.translate(glm.rotate(glm.translate(M_zum, glm.vec3(-0.42, 0.0, 0.15)),
                                  osc, glm.vec3(1, 0, 0)), glm.vec3(0, 0, 0.25)),
        glm.vec3(0.14, 0.14, 0.50))
    M_braco_esq = glm.scale(
        glm.translate(glm.rotate(glm.translate(M_zum, glm.vec3( 0.42, 0.0, 0.15)),
                                 -osc, glm.vec3(1, 0, 0)), glm.vec3(0, 0, 0.25)),
        glm.vec3(0.14, 0.14, 0.50))

    # 5. Objetos da cena: (malha, textura, material, matriz modelo)
    cena = [
        ("piso",      "piso",      MATERIAIS[2], glm.scale(glm.translate(giro, glm.vec3(0, -0.25, 0)), glm.vec3(12, 0.5, 8))),
        ("pilar",     "piso",      MATERIAIS[2], glm.scale(glm.translate(giro, glm.vec3(-4, 1.5, -2)), glm.vec3(0.8, 3, 0.8))),
        ("cavaleiro", "cavaleiro", MATERIAIS[1], M_cav * objetos["cavaleiro"].enquadramento),
        ("pilar",     "cavaleiro", MATERIAIS[1], M_espada),
        ("zumbi",     "zumbi",     MATERIAIS[0], M_zum * objetos["zumbi"].enquadramento),
        ("pilar",     "zumbi",     MATERIAIS[0], M_braco_dir),
        ("pilar",     "zumbi",     MATERIAIS[0], M_braco_esq),
    ]

    for obj, tex, mat, M in cena:
        texs[tex].use(0)
        enviar(prog, u_modelo=M, u_normal=matriz_normal(M),
               u_ka=mat.ka, u_kd=mat.kd, u_ks=mat.ks, u_alfa=mat.alfa)
        objetos[obj].desenhar()


def main():
    glfw.set_error_callback(erro_glfw)
    if not glfw.init():
        sys.exit("FALHA: glfw nao inicializou")

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)
    glfw.window_hint(glfw.SAMPLES, 4)
    glfw.window_hint(glfw.SRGB_CAPABLE, True)

    janela = glfw.create_window(LARGURA, ALTURA,
                                "Cavaleiro vs Zumbis", None, None)
    if not janela:
        glfw.terminate()
        sys.exit("FALHA: nao foi possivel criar a janela")

    glfw.make_context_current(janela)
    glfw.swap_interval(1)
    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.enable(moderngl.CULL_FACE)

    prog = carregar_programa(ctx, "cena")

    objetos = {
        "cavaleiro": MalhaGPU.de_off(ctx, prog, AQUI / "off" / "cavaleiro.off"),
        "zumbi":     MalhaGPU.de_off(ctx, prog, AQUI / "off" / "zumbi.off"),
        "piso":      MalhaGPU(ctx, prog, *criar_cubo(uv_escala=8.0)),
        "pilar":     MalhaGPU(ctx, prog, *criar_cubo(uv_escala=1.0)),
    }

    def carregar_tex(ctx, nome):
        tex = tx.carregar(ctx, abrir(nome), srgb=True, mipmap=True)
        tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        return tex

    texs = {
        "piso":      carregar_tex(ctx, "piso.jpg"),
        "cavaleiro": carregar_tex(ctx, "MetalKnight.jpg"),
        "zumbi":     carregar_tex(ctx, "Moss.jpg"),
    }

    mod_camera.RAIO_MODELO = 8.0
    mod_camera.NEAR_MIN = 0.2
    camera = mod_camera.Camera(distancia=13.0)

    bola = Trackball()
    bola.orientacao = glm.angleAxis(glm.radians(22.0), glm.vec3(1.0, 0.0, 0.0))

    # Luz 1: direcional (holofote/luar) -> w = 0.0
    luz_dir = Luz()
    luz_dir.posicao = glm.vec4(0.4, 1.0, 0.5, 0.0)
    luz_dir.ia = glm.vec3(0.35, 0.40, 0.55)
    luz_dir.id = glm.vec3(0.55, 0.62, 0.80)
    luz_dir.is_ = glm.vec3(0.55, 0.62, 0.80)

    # Luz 2: pontual dourada seguindo o cavaleiro -> w = 1.0
    luz_pont = Luz()
    luz_pont.ia = glm.vec3(0.10, 0.07, 0.02)
    luz_pont.id = glm.vec3(1.00, 0.78, 0.35)
    luz_pont.is_ = glm.vec3(1.00, 0.85, 0.50)

    def tecla(window, key, scancode, action, mods):
        if action != glfw.PRESS:
            return
        if key == glfw.KEY_ESCAPE:
            glfw.set_window_should_close(window, True)
        elif key == glfw.KEY_W:
            estado["aramado"] = not estado["aramado"]
        elif key == glfw.KEY_C:
            estado["descarte"] = not estado["descarte"]
        elif key == glfw.KEY_Z:
            bola.zerar()
        elif key == glfw.KEY_B:
            estado["blinn"] = not estado["blinn"]
        elif key == glfw.KEY_T:
            estado["cartoon"] = not estado["cartoon"]
        elif key == glfw.KEY_L:
            estado["luz_pontual"] = not estado["luz_pontual"]
        elif key == glfw.KEY_Q:
            estado["cam_orbital"] = not estado["cam_orbital"]
        elif key == glfw.KEY_SPACE and estado["golpe"] == 0.0 and not estado["game_over"]:
            estado["golpe"] = DURACAO_GOLPE
        elif key == glfw.KEY_R:
            reiniciar()

    def botao(window, button, action, mods):
        if not estado["cam_orbital"] or button != glfw.MOUSE_BUTTON_LEFT:
            return
        x, y = glfw.get_cursor_pos(window)
        if action == glfw.PRESS:
            bola.pressionar(x, y)
        elif action == glfw.RELEASE:
            bola.soltar()

    def roda(window, dx, dy):
        if not estado["cam_orbital"]:
            return
        camera.distancia = float(np.clip(
            camera.distancia - dy * PASSO_ZOOM, ZOOM_MIN, ZOOM_MAX))

    def redimensionou(window, largura, altura):
        largura, altura = max(1, largura), max(1, altura)
        ctx.viewport = (0, 0, largura, altura)
        camera.aspecto = largura / altura
        lj, aj = glfw.get_window_size(window)
        bola.redimensionar(max(1, lj), max(1, aj))

    glfw.set_key_callback(janela, tecla)
    glfw.set_mouse_button_callback(janela, botao)
    glfw.set_scroll_callback(janela, roda)
    glfw.set_framebuffer_size_callback(janela, redimensionou)
    redimensionou(janela, *glfw.get_framebuffer_size(janela))

    instante_anterior = glfw.get_time()

    while not glfw.window_should_close(janela):
        agora = glfw.get_time()
        dt = min(agora - instante_anterior, DT_MAXIMO)
        instante_anterior = agora
        estado["tempo"] = agora

        if not estado["game_over"]:
            esq = (glfw.get_key(janela, glfw.KEY_A) == glfw.PRESS or
                   glfw.get_key(janela, glfw.KEY_LEFT) == glfw.PRESS)
            dir_ = (glfw.get_key(janela, glfw.KEY_D) == glfw.PRESS or
                    glfw.get_key(janela, glfw.KEY_RIGHT) == glfw.PRESS)
            mov = float(dir_) - float(esq)
            if mov != 0.0:
                estado["cav_dir"] = mov
                estado["cav_x"] = max(-LIMITE_X, min(LIMITE_X,
                                      estado["cav_x"] + mov * VEL_CAV * dt))

            estado["golpe"] = max(0.0, estado["golpe"] - dt)

            sentido_z = 1.0 if estado["cav_x"] > estado["zumbi_x"] else -1.0
            estado["zumbi_x"] += sentido_z * estado["zumbi_vel"] * dt

            espada_x = estado["cav_x"] + estado["cav_dir"] * 0.9
            if estado["golpe"] > 0.0 and colidiu(espada_x, MEIO_ESPADA,
                                                 estado["zumbi_x"], MEIO_BONECO):
                estado["pontos"] += 1
                estado["zumbi_vel"] += PASSO_VEL
                estado["zumbi_x"] = random.choice([-SPAWN_X, SPAWN_X])
            elif colidiu(estado["cav_x"], MEIO_BONECO,
                         estado["zumbi_x"], MEIO_BONECO):
                estado["game_over"] = True

        if estado["cam_orbital"]:
            if bola.arrastando:
                bola.mover(*glfw.get_cursor_pos(janela), dt)
            else:
                bola.atualizar(dt)

        desenhar_quadro(ctx, prog, objetos, texs, luz_dir, luz_pont,
                        estado, camera, bola)
        glfw.swap_buffers(janela)
        glfw.poll_events()

        if estado["game_over"]:
            glfw.set_window_title(janela, f"GAME OVER - Pontos: {estado['pontos']} (R reinicia)")
        else:
            cam = "Orbital" if estado["cam_orbital"] else "Lateral"
            glfw.set_window_title(
                janela,
                f"Cavaleiro vs Zumbis | Pontos: {estado['pontos']} | "
                f"Vel: {estado['zumbi_vel']:.1f} | Cam: {cam} [Q]")

    for obj in objetos.values():
        obj.liberar()
    for t in texs.values():
        t.release()
    prog.release()
    glfw.terminate()


if __name__ == "__main__":
    main()