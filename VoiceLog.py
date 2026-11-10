import json
import os
import re
import subprocess
import tempfile
import sys
from pathlib import Path

import imageio_ffmpeg
import requests
from flask import Flask, jsonify, render_template, request

# Windows terminals may use a legacy code page that cannot print
# Tamil/other Unicode text returned by speech recognition. Avoid crashing
# while logging such text.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(errors="backslashreplace")

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
EXPENSES_FILE = BASE_DIR / "expenses.json"

# Set these environment variables before starting the application.
# Do not put your API key directly in this file.
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "").strip()
GNANI_API_URL = os.getenv(
    "GNANI_API_URL",
    "https://api.vachana.ai/stt/v3"
).strip()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


def read_expenses():
    if not EXPENSES_FILE.exists():
        return []

    try:
        with EXPENSES_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


@app.route("/get-expenses", methods=["GET"])
def get_expenses():
    return jsonify(read_expenses())


def classify_expense(transcript):
    text = transcript.lower()

    if any(word in text for word in [
        "cab", "auto", "train", "bus", "travel", "taxi", "metro"
    ]):
        return "Travel"

    if any(word in text for word in [
        "lunch", "coffee", "food", "dinner", "tea", "breakfast",
        "restaurant", "snack", "water", "juice", "milk",
        "pizza", "burger", "meal", "cafe"
    ]):
        return "Food & Dining"


    if any(word in text for word in [
        "book", "notebook", "pen", "stationery"
    ]):
        return "Education"

    if any(word in text for word in [
        "medicine", "doctor", "hospital", "pharmacy"
    ]):
        return "Healthcare"

    if any(word in text for word in [
        "movie", "game", "entertainment"
    ]):
        return "Entertainment"

    return "General"




def parse_expense_items(transcript):

    # Separate individual expenses.
    parts = re.split(
        r"\s*(?:,|;|\bappuram\b|\bthen\b|\band\b)\s*",
        transcript,
        flags=re.IGNORECASE
    )

    items = []

    for part in parts:
        amount_match = re.search(
            r"(?<!\w)\d[\d,]*(?:\.\d{1,2})?(?!\w)",
            part
        )

        if not amount_match:
            continue

        amount = amount_match.group().replace(",", "")

        # Remove the amount to identify the expense item.
        item = part[:amount_match.start()] + part[amount_match.end():]

        item = re.sub(
            r"\b(?:rupees?|rs|inr|roob|only|for|spent|spend|on|the|and|appuram|i|paid)\b",
            " ",
            item,
            flags=re.IGNORECASE
        )

        # Remove Tamil-English suffix.
        item = re.sub(
            r"[-\s]*ku\b",
            " ",
            item,
            flags=re.IGNORECASE
        )

        item = re.sub(r"[^\w\s&-]", " ", item)
        item = re.sub(r"\s+", " ", item).strip()

        if not item:
            item = "Expense"

        items.append({
            "item": item.title(),
            "amount": amount,
            "category": classify_expense(item)
        })

    if not items:
        raise ValueError(
            "No recognizable expense amounts were found in the transcript."
        )

    return items


def save_expenses(transcript):
    """
    Save every extracted item as a separate expense.
    Preserve the original transcript for reference.
    """

    items = parse_expense_items(transcript)
    expenses = read_expenses()

    saved_items = []

    for item in items:
        expense = {
            "item": item["item"],
            "amount": item["amount"],
            "category": item["category"],
            "transcript": item["item"],
            "raw_transcript": transcript
        }

        expenses.append(expense)
        saved_items.append(expense)

    with EXPENSES_FILE.open("w", encoding="utf-8") as file:
        json.dump(expenses, file, indent=4, ensure_ascii=False)

    return saved_items



def convert_audio_to_wav(input_path, output_path):
    """
    Convert the browser-recorded audio to standard PCM WAV.
    imageio-ffmpeg supplies the FFmpeg executable, so a separate
    system-wide FFmpeg installation is not required.
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    command = [
        ffmpeg_exe,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(output_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        error_message = (result.stderr or "Unknown FFmpeg conversion error").strip()
        raise ValueError("Audio conversion failed: " + error_message[-1200:])

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise ValueError("Audio conversion failed: WAV output is empty.")


@app.route("/process-audio", methods=["POST"])
def process_audio():
    if "audio" not in request.files:
        return jsonify({
            "success": False,
            "error": "No audio file was received."
        }), 400

    audio_file = request.files["audio"]

    if not audio_file or not audio_file.filename:
        return jsonify({
            "success": False,
            "error": "The uploaded audio file is empty."
        }), 400

    if not GNANI_API_KEY:
        return jsonify({
            "success": False,
            "error": "GNANI_API_KEY is not configured."
        }), 500

    # Use the browser's filename extension to identify the input container.
    # FFmpeg reads the actual file content; the extension is only a hint.
    original_name = audio_file.filename.lower()
    suffix = Path(original_name).suffix
    if suffix not in {".ogg", ".webm", ".m4a", ".mp4", ".wav", ".mp3", ".aac"}:
        suffix = ".audio"

    input_path = None
    wav_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
            dir=BASE_DIR
        ) as temp_file:
            input_path = Path(temp_file.name)
            audio_file.save(temp_file)

        wav_handle = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav",
            dir=BASE_DIR
        )
        wav_path = Path(wav_handle.name)
        wav_handle.close()

        # Convert WebM/OGG/MP4 recordings to a format accepted by Gnani.
        convert_audio_to_wav(input_path, wav_path)

        headers = {
            "X-API-Key-ID": GNANI_API_KEY
        }

        # Keep the existing endpoint and request fields from this project.
        # If the competition's current API documentation specifies different
        # fields, those must take precedence.
        with wav_path.open("rb") as audio_stream:
            uploaded_files = {
                "audio_file": (
                    "voice_note.wav",
                    audio_stream,
                    "audio/wav"
                )
            }
            form_data = {
                "model": "prisma-v3.0",
                "language_code": "en-IN",
                "format": "transcribe"
            }

            response = requests.post(
                GNANI_API_URL,
                headers=headers,
                files=uploaded_files,
                data=form_data,
                timeout=60
            )

        print("Gnani HTTP status:", response.status_code)
        print("Gnani response:", response.text[:3000])

        response.raise_for_status()

        try:
            result = response.json()
        except ValueError:
            return jsonify({
                "success": False,
                "error": "Gnani returned a response that was not valid JSON.",
                "provider_response": response.text[:1000]
            }), 502

        if result.get("success") is not True:
            return jsonify({
                "success": False,
                "error": "Gnani did not report a successful transcription.",
                "provider_response": result
            }), 502

        transcript = str(result.get("transcript") or "").strip()

        if not transcript:
            return jsonify({
                "success": False,
                "error": "Gnani returned an empty transcript.",
                "provider_response": result
            }), 502

       
        expenses = save_expenses(transcript)

        return jsonify({
            "success": True,
            "transcript": transcript,
            "expenses": [
                {
                    "item": expense["item"],
                    "amount": expense["amount"],
                    "category": expense["category"]
                }
                for expense in expenses
            ],
            "amount": expenses[0]["amount"],
            "category": expenses[0]["category"]
        })



    except requests.Timeout:
        return jsonify({
            "success": False,
            "error": "Gnani API request timed out. Please try again."
        }), 504

    except requests.RequestException as error:
        provider_message = ""
        if getattr(error, "response", None) is not None:
            provider_message = error.response.text[:1000]

        print("Gnani request error:", str(error))
        print("Gnani provider error:", provider_message)

        return jsonify({
            "success": False,
            "error": "Gnani API request failed.",
            "details": str(error),
            "provider_response": provider_message
        }), 502

    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print("Audio processing error:", str(error))
        return jsonify({
            "success": False,
            "error": str(error)
        }), 400

    except Exception as error:
        app.logger.exception("Unexpected audio-processing error")
        return jsonify({
            "success": False,
            "error": "Unexpected server error: " + str(error)
        }), 500

    finally:
        for temp_path in (input_path, wav_path):
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    app.logger.warning(
                        "Could not remove temporary audio file: %s",
                        temp_path
                    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )
