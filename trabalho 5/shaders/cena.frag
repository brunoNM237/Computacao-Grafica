#version 400 core

// Sombreamento de Phong: a equacao e avaliada uma vez por
// fragmento, com a posicao e a normal interpoladas.

in vec3 fP;
in vec3 fN;
in vec2 fTexCoord;

uniform sampler2D u_base;
uniform bool u_usar_textura;
uniform vec3 u_olho;

// Duas fontes de luz: direcional (w = 0) e pontual (w = 1)
uniform vec4 u_luz_dir;
uniform vec3 u_ia_dir, u_id_dir, u_is_dir;

uniform vec4 u_luz_pont;
uniform vec3 u_ia_pont, u_id_pont, u_is_pont;

uniform vec3 u_ka, u_kd, u_ks;
uniform float u_alfa;
uniform bool u_blinn;
uniform bool u_cartoon;
uniform int u_niveis;        // numero de niveis do cartoon
uniform bool u_sem_luz;

out vec4 outfragcolor;

// Cartoon: o maior multiplo de 1/u_niveis que nao ultrapassa f.
float quantizar(float f) {
    return floor(f * float(u_niveis)) / float(u_niveis);
}

vec3 phong(vec3 P, vec3 N, vec3 kd,
           vec4 luz, vec3 ia, vec3 id, vec3 is_) {
  

    vec3 L;
    float atenuacao = 1.0;

    if (luz.w == 1.0) {
        vec3 delta = luz.xyz - P;        // pontual
        float d = length(delta);
        L = delta / d;
        atenuacao = 1.0 / (1.0 + 0.09 * d + 0.032 * d * d);
    } else {
        L = normalize(luz.xyz);          // direcional
    }

    vec3 V = normalize(u_olho - P);      // camera no espaco do mundo
    float NdotL = max(dot(N, L), 0.0);

    vec3 ambiente = u_ka * ia;
    vec3 difusa   = kd * id * NdotL;
    if (u_cartoon) difusa = kd * id * quantizar(NdotL);

    // sem brilho especular onde a luz nao chega
    float brilho = 0.0;
    if (NdotL > 0.0) {
        if (u_blinn) {
            vec3 H = normalize(L + V);
            brilho = pow(max(dot(N, H), 0.0), u_alfa);
        } else {
            vec3 R = reflect(-L, N);
            brilho = pow(max(dot(R, V), 0.0), u_alfa);
        }
    }
    return atenuacao * (ambiente + difusa + u_ks * is_ * brilho);
}

void main() {
    if (u_sem_luz) {
        outfragcolor = vec4(u_kd, 1.0);
        return;
    }    


    vec3 N = normalize(fN);    // a interpolacao encurta a normal
    vec3 kd = u_usar_textura ? texture(u_base, fTexCoord).rgb : u_kd;

    vec3 cor = phong(fP, N, kd, u_luz_dir,  u_ia_dir,  u_id_dir,  u_is_dir)
             + phong(fP, N, kd, u_luz_pont, u_ia_pont, u_id_pont, u_is_pont);

    outfragcolor = vec4(cor, 1.0);
}