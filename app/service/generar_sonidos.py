import wave
import struct
import math

def generar_seno(nombre, frecuencia=440, duracion=0.5, volumen=0.5, sample_rate=44100):
    """
    Genera un archivo WAV con un tono seno.
    """
    n_samples = int(sample_rate * duracion)
    archivo = wave.open(nombre, 'w')
    archivo.setparams((1, 2, sample_rate, n_samples, "NONE", "not compressed"))

    for i in range(n_samples):
        valor = volumen * math.sin(2 * math.pi * frecuencia * (i / sample_rate))
        archivo.writeframes(struct.pack('<h', int(valor * 32767.0)))

    archivo.close()
    print(f"✅ Generado: {nombre}")

# ⚠️ Generar sonidos
generar_seno("alerta_fuerte.wav", frecuencia=220, duracion=0.7, volumen=0.9)   # grave, fuerte
generar_seno("aviso_leve.wav", frecuencia=880, duracion=0.3, volumen=0.5)    # agudo, leve
