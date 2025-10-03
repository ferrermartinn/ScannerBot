# -*- coding: utf-8 -*-
"""
sonidos.py — módulo de sonidos con fallbacks.
- pygame (si está) -> reproduce WAVs ('aviso_leve.wav', 'alerta_fuerte.wav') con volumen.
- winsound (Windows) -> vibrido/beep como fallback.
- si no hay backend, no rompe (silencioso).
- Respeta config.json (mute y volúmenes) vía config.py
"""

import os
import sys
from typing import Optional
from app.core.config import load_config, is_muted, get_volume


# Config helpers (no fallan si no existe; crean defaults)
try:
    from config import load_config, is_muted, get_volume
except Exception:
    # Fallback mini-helpers si config.py no está por algún motivo
    def load_config():
        return {"mute_alerts": False, "vol_sounds": {"alerta_vibrido": 0.2, "alerta_precio": 0.4, "alerta_rentable": 0.9}}
    def is_muted(cfg=None): 
        cfg = cfg or load_config(); 
        return bool(cfg.get("mute_alerts", False))
    def get_volume(name, default=0.3, cfg=None):
        cfg = cfg or load_config()
        try: return float((cfg.get("vol_sounds") or {}).get(name, default))
        except Exception: return default

# Backends opcionales
_BACKEND = None
try:
    import pygame
    _BACKEND = "pygame"
except Exception:
    try:
        import winsound as _ws  # Windows
        _BACKEND = "winsound"
    except Exception:
        _BACKEND = None

_PYG_INIT = False
_SOUNDS = {}

def _pygame_init():
    global _PYG_INIT
    if _PYG_INIT: 
        return
    try:
        os.environ.setdefault("SDL_AUDIODRIVER", "directsound")  # ayuda en Windows
        pygame.mixer.init()
        _PYG_INIT = True
    except Exception as e:
        print(f"[sonidos] pygame init falló: {e}", file=sys.stderr)

def _pygame_load(name: str, path: str):
    """Carga y cachea un sonido pygame si el archivo existe."""
    if not _PYG_INIT: 
        _pygame_init()
    if not _PYG_INIT:
        return None
    if not os.path.exists(path):
        return None
    try:
        if name not in _SOUNDS:
            _SOUNDS[name] = pygame.mixer.Sound(path)
        return _SOUNDS[name]
    except Exception as e:
        print(f"[sonidos] no pude cargar {path}: {e}", file=sys.stderr)
        return None

def vibrido_suave(volumen: Optional[float] = None, duracion: float = 0.14, frecuencia: float = 180.0):
    """Vibrido muy leve (tipo celular). Respeta mute y volumen 'alerta_vibrido'."""
    cfg = load_config()
    if is_muted(cfg):
        return
    vol = get_volume("alerta_vibrido", default=0.2, cfg=cfg) if volumen is None else float(volumen)

    if _BACKEND == "pygame":
        snd = _pygame_load("buzz", "aviso_leve.wav")
        if snd:
            try:
                snd.set_volume(max(0.0, min(1.0, vol)))
                snd.play()
                return
            except Exception:
                pass
    if _BACKEND == "winsound":
        try:
            _ws.Beep(int(frecuencia), int(duracion * 1000))
            return
        except Exception:
            pass
    # Silencioso si no hay backend
    print("[sonidos] (silencioso) vibrido_suave", file=sys.stderr)

def aviso_leve():
    """Alias para vibrido_suave (notificación tenue)."""
    vibrido_suave()

def alerta_fuerte(volumen: Optional[float] = None):
    """
    Alerta más marcada (oportunidad fuerte). 
    - Intenta reproducir 'alerta_fuerte.wav' con pygame.
    - Fallback en winsound: dos beeps cortos.
    """
    cfg = load_config()
    if is_muted(cfg):
        return
    vol = get_volume("alerta_rentable", default=0.9, cfg=cfg) if volumen is None else float(volumen)

    if _BACKEND == "pygame":
        snd = _pygame_load("alerta", "alerta_fuerte.wav")
        if snd:
            try:
                snd.set_volume(max(0.0, min(1.0, vol)))
                snd.play()
                return
            except Exception:
                pass
    if _BACKEND == "winsound":
        try:
            _ws.Beep(700, 140); _ws.Beep(650, 120)
            return
        except Exception:
            pass
    print("[sonidos] (silencioso) alerta_fuerte", file=sys.stderr)

def alerta_precio():
    """Placeholder genérico (usa vibrido suave)."""
    vibrido_suave()

def alerta_rentable():
    """Compat: usa alerta_fuerte."""
    alerta_fuerte()

def backend():
    """Devuelve backend activo para debug."""
    return _BACKEND
