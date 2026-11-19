#!/usr/bin/env python3
"""Similarité de voix (ECAPA, speechbrain) entre une référence et des prises. Sortie : JSON {fichier: cosinus}.

  <python avec torch, librosa, speechbrain> speaker_similarity.py reference.wav prise1.wav [prise2.wav ...]

Lancé par voice_scenes.py avec VOICE_EVAL_PYTHON (par défaut, le Python embarqué de VoiceStudio).
"""
import json, os, sys, warnings
warnings.filterwarnings("ignore")
import librosa, torch  # noqa: E402
from speechbrain.inference.speaker import EncoderClassifier  # noqa: E402

cache = os.path.join(os.path.expanduser("~"), ".cache", "agent-montage-video", "ecapa-voxceleb")
enc = EncoderClassifier.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb", savedir=cache, run_opts={"device": "cpu"})


def emb(path):
    y, _ = librosa.load(path, sr=16000)
    with torch.no_grad():
        return enc.encode_batch(torch.from_numpy(y)[None]).squeeze()


ref = emb(sys.argv[1])
print(json.dumps({f: float(torch.nn.functional.cosine_similarity(ref, emb(f), dim=0)) for f in sys.argv[2:]}))

