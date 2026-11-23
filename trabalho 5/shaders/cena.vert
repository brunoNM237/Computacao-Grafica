#version 400 core

// Mesmo padrao de ambiente.vert: OpenGL preenche w = 1.0 quando o VBO envia 3f
layout(location = 0) in vec4 vPosition;
layout(location = 1) in vec3 vNormal;
layout(location = 2) in vec2 vTexCoord;

uniform mat4 u_modelo, u_visao, u_projecao;
uniform mat3 u_normal;       // inversa transposta de u_modelo

out vec3 fP;                 // posicao no mundo
out vec3 fN;                 // normal no mundo
out vec2 fTexCoord;

void main() {
    vec4 pos_mundo = u_modelo * vPosition;
    gl_Position = u_projecao * u_visao * pos_mundo;
    fP = pos_mundo.xyz;
    fN = u_normal * vNormal;
    fTexCoord = vTexCoord;
}