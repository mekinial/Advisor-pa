"""Turn a Telegram voice note (or any audio file) into text, locally on this computer (faster-whisper, no upload).

  ./pa transcribe "<audio path>"

Prints the transcript. First run downloads the speech model once (~480 MB, "small"; good with Singapore English).
The Telegram line gets the file with download_attachment, then runs this.
"""
import sys, os

if len(sys.argv) < 2 or not os.path.isfile(sys.argv[1]):
    sys.exit(__doc__)
os.environ.setdefault("HF_HOME", os.path.join(os.path.expanduser("~"), ".advisor-pa", "models"))
import numpy as np, av
from faster_whisper import WhisperModel


def decode(path):  # own decoder: faster-whisper's passes an option newer PyAV no longer accepts
    rs = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=16000)
    chunks = []
    with av.open(path) as c:
        for frame in c.decode(audio=0):
            for f in rs.resample(frame):
                chunks.append(f.to_ndarray().reshape(-1))
    for f in rs.resample(None):
        chunks.append(f.to_ndarray().reshape(-1))
    return np.concatenate(chunks).astype(np.float32) / 32768.0


model = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
segments, info = model.transcribe(decode(sys.argv[1]), language="en", vad_filter=True, beam_size=5,
                                  initial_prompt="Singapore financial adviser notes: clients, policies, premiums, "
                                                 "Great Eastern, CPF, MediShield, follow up, referral.")
print(" ".join(s.text.strip() for s in segments).strip() or "(no speech found)")
