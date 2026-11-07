"""Local speech synthesis. No accounts, GPU, or outbound requests for eSpeak."""
import asyncio
import ctypes
import functools
import threading
import wave
from .config import settings

VOICES = [
    {'id': 'local-neutral', 'name': 'Clear', 'description': 'American · Neutral synthetic voice'},
    {'id': 'local-warm', 'name': 'Bright', 'description': 'American · Higher synthetic voice'},
    {'id': 'local-bright', 'name': 'Classic', 'description': 'British · Neutral synthetic voice'},
]
PROFILES = {
    'local-neutral': ('en-us', 46, 155),
    'local-warm': ('en-us+f3', 62, 155),
    'local-bright': ('en', 53, 160),
    # Legacy saved scripts/configurations can still render in local mode.
    'en-US-JennyNeural': ('en-us+f3', 62, 155),
    'en-US-GuyNeural': ('en-us', 46, 155),
    'en-GB-SoniaNeural': ('en', 53, 160),
}
_lock = threading.Lock()


@functools.lru_cache(maxsize=1)
def espeak_runtime():
    import espeakng_loader
    library = ctypes.CDLL(espeakng_loader.get_library_path())
    library.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    library.espeak_Initialize.restype = ctypes.c_int
    rate = library.espeak_Initialize(2, 0, espeakng_loader.get_data_path().encode(), 0)
    if rate <= 0:
        raise ValueError('The local speech engine could not initialize.')
    library.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
    library.espeak_SetParameter.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
    library.espeak_Synth.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_int,
                                   ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
    return library, rate


@functools.lru_cache(maxsize=1)
def loudkit_runtime():
    try:
        import loudkit as lk
    except ImportError as exc:
        raise ValueError('Install requirements-loudkit.txt and download the model before choosing loudkit.') from exc
    return lk.load(settings.loudkit_model, revision=settings.loudkit_revision, device='cpu')


def synthesize(text, voice, destination, cancelled=None):
    """Serialize access to the native/global voice engine; retain neural engine across jobs."""
    with _lock:
        if cancelled and cancelled.is_set():
            return
        if settings.local_tts_engine == 'loudkit':
            engine = loudkit_runtime()
            # One pinned English neural voice. eSpeak profiles are not neural voice identities.
            result = engine.synthesize(text, engine.voice('joe'), seed=7,
                                       should_cancel=cancelled.is_set if cancelled else None)
            result.save(str(destination))  # loudkit writes its synthetic-audio provenance note.
            return
        library, sample_rate = espeak_runtime()
        name, pitch, speed = PROFILES[voice]
        if library.espeak_SetVoiceByName(name.encode()) != 0:
            raise ValueError('The requested offline voice is unavailable.')
        library.espeak_SetParameter(1, speed, 0)  # RATE (words/minute)
        library.espeak_SetParameter(3, pitch, 0)  # PITCH
        samples = []
        callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p)
        def collect(pointer, count, events):
            if cancelled and cancelled.is_set():
                return 1
            if pointer and count:
                samples.append(ctypes.string_at(pointer, count * 2))
            return 0
        callback = callback_type(collect)
        library.espeak_SetSynthCallback.argtypes = [callback_type]
        library.espeak_SetSynthCallback(callback)
        data = text.encode('utf-8') + b'\0'
        code = library.espeak_Synth(data, len(data), 0, 1, 0, 1 | 0x1000, None, None)
        library.espeak_Synchronize()
        if code or not samples:
            raise ValueError('The offline voice engine returned no audio.')
        with wave.open(str(destination), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(sample_rate)
            output.writeframes(b''.join(samples))


async def speak(text, voice, destination):
    cancelled = threading.Event()
    task = asyncio.create_task(asyncio.to_thread(synthesize, text, voice, destination, cancelled))
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        cancelled.set()
        try:
            await task
        except Exception:
            pass
        raise
