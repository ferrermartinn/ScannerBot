import numpy as np
import wave
import struct

def generar_seno(frequency, duration, volume, filename):
    framerate = 44100
    n_samples = int(framerate * duration)
    amplitude = 32767 * volume
    t = np.linspace(0, duration, n_samples, False)

    # onda senoidal
    signal = amplitude * np.sin(2 * np.pi * frequency * t)

    # guardar a wav
    with wave.open(filename, 'w') as wav_file:
        wav_file.setparams((1, 2, framerate, n_samples, "NONE", "not compressed"))
        for s in signal:
            wav_file.writeframes(struct.pack('h', int(s)))

# sonido fuerte (alarma, agudo)
generar_seno(1000, 0.5, 1.0, "alerta_fuerte.wav")

# sonido leve (notificación, más suave)
generar_seno(400, 0.3, 0.5, "aviso_leve.wav")

print("✅ Archivos de sonido generados: alerta_fuerte.wav y aviso_leve.wav")
