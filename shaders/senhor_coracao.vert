#version 400 core

layout(location = 0) in vec4 vPosition;

uniform float u_escala;
uniform vec2  u_deslocamento;
uniform vec4  u_cor;
uniform float u_angulo;

out vec4 v2fcolor;

void main() {
    mat2 rot = mat2(
        cos(u_angulo),  sin(u_angulo),
       -sin(u_angulo),  cos(u_angulo)
    );

    vec2 pos_rotacionada = rot * vPosition.xy;
    vec2 pos_final = (pos_rotacionada * u_escala) + u_deslocamento;

    v2fcolor = u_cor;
    gl_Position = vec4(pos_final, 0.0, 1.0);
}
