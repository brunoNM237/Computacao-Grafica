"""Leitura de imagens e criacao de texturas.

O formato interno depende do que a imagem guarda:
  cor  (fotos, texturas difusas, mapa cubico) -> GL_SRGB8_ALPHA8,
       e o OpenGL decodifica os texels na leitura;
  dado (mapas de normais, mascaras)           -> GL_RGBA8,
       e os valores chegam ao shader como estao no arquivo.
"""
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image

# Constantes do OpenGL que o moderngl nao exporta por nome.
GL_SRGB8_ALPHA8 = 0x8C43
GL_RGBA8 = 0x8058

# Filtragem anisotropica: ate 8 amostras ao longo do lado maior da
# projecao do pixel sobre a textura.
ANISOTROPIA_MAX = 8.0

# Ordem das faces de um mapa cubico no OpenGL.
FACES = ["posx", "negx", "posy", "negy", "posz", "negz"]


def ler(caminho):
    """Imagem como array (altura, largura, 4), linha 0 em cima."""
    return np.asarray(Image.open(caminho).convert("RGBA"),
                      dtype='u1').copy()


def carregar(ctx, imagem, srgb, mipmap=True):
    """Envia a imagem para a GPU. srgb: True para cor, False para
    dado (sem valor padrao, de proposito)."""
    altura, largura = imagem.shape[:2]
    formato = GL_SRGB8_ALPHA8 if srgb else GL_RGBA8
    # [::-1]: a primeira linha enviada e a de t = 0, a de baixo.
    tex = ctx.texture((largura, altura), 4,
                      np.ascontiguousarray(imagem[::-1]).tobytes(),
                      internal_format=formato)
    # GL_REPEAT: a costura (u + 1), as repeticoes do modo 0 e o
    # deslocamento das nuvens do modo 9 saem de [0, 1].
    tex.repeat_x = tex.repeat_y = True
    if mipmap:
        tex.build_mipmaps()
        tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        tex.anisotropy = min(ANISOTROPIA_MAX, ctx.max_anisotropy)
    else:
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
    return tex


def carregar_cubo(ctx, pasta):
    """Le posx.jpg ... negz.jpg e cria um mapa cubico.

    A tabela de faces do OpenGL e de mao esquerda. Para o nosso mundo,
    de mao direita, o ambiente e espelhado em z: trocam-se as faces
    +z e -z, invertem-se as linhas de +y e -y e as colunas das
    demais. 
    """
    faces = {}
    for nome in FACES:
        img = ler(next(Path(pasta).glob(nome + ".*")))
        if nome in ("posy", "negy"):
            img = img[::-1]               # inverte as linhas
        else:
            img = img[:, ::-1]            # inverte as colunas
        faces[nome] = img
    faces["posz"], faces["negz"] = faces["negz"], faces["posz"]

    lado = faces["posx"].shape[0]
    dados = b"".join(np.ascontiguousarray(faces[n]).tobytes()
                     for n in FACES)
    tex = ctx.texture_cube((lado, lado), 4, dados,
                           internal_format=GL_SRGB8_ALPHA8)
    tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
    return tex
