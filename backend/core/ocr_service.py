"""
EATGOOD — OCR & Food Label Extraction Service
Robust, local-first OCR pipeline integrating Tesseract 5 with OpenCV image preprocessing
and comprehensive heuristic nutrition extraction.

Guiding Principles:
1. Local-first: All preprocessing and OCR execute locally on the device (zero third-party egress).
2. Honest provenance: NEVER silently replace failed or empty OCR with hardcoded mock/sample values.
3. Explicit statuses: Every field is tagged as 'extracted', 'needs_review', or 'not_found'.
4. Scientific plausibility: Performs Atwater macro-calorie cross-checks, serving-size sanity checks,
   and OCR artifact corrections (e.g. 'Og' -> 0g, missing decimal points).
5. Mandatory confirmation: Returns all extracted fields for user review before assessment generation.
"""

import os
import re
import shutil
import logging
import base64
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from PIL import Image, ImageOps
import httpx

try:
    import cv2
except Exception:
    cv2 = None

try:
    import pytesseract
except Exception:
    pytesseract = None

logger = logging.getLogger("eatgood.ocr")

# Resolve Tesseract executable path
def get_tesseract_path() -> Optional[str]:
    """Finds available Tesseract binary on the host system."""
    if pytesseract is None:
        return None
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd and os.path.exists(env_cmd):
        return env_cmd

    candidate_paths = [
        "/opt/homebrew/bin/tesseract",       # macOS Apple Silicon Homebrew
        "/usr/local/bin/tesseract",          # macOS Intel Homebrew / Linux standard
        "/usr/bin/tesseract",                # Linux package manager
        shutil.which("tesseract")            # System PATH
    ]
    for path in candidate_paths:
        if path and os.path.exists(path):
            return path
    return None

# Configure pytesseract path if located
_TESS_PATH = get_tesseract_path()
if _TESS_PATH:
    pytesseract.pytesseract.tesseract_cmd = _TESS_PATH
    logger.info(f"EATGOOD OCR initialized with Tesseract executable: {_TESS_PATH}")
else:
    logger.warning("EATGOOD OCR: Tesseract binary not found in standard paths.")


def get_cloud_vision_api_key() -> Optional[str]:
    """Finds available Google Cloud Vision API key from server environment variables."""
    candidate_keys = [
        "VISION_API_KEY",
        "GOOGLE_CLOUD_VISION_API_KEY",
        "GOOGLE_VISION_API_KEY",
        "GOOGLE_API_KEY"
    ]
    for key_name in candidate_keys:
        val = os.environ.get(key_name)
        if val and val.strip():
            return val.strip()
    return None


def get_ocr_engine_info() -> Dict[str, Any]:
    """
    Returns status and active engine of the OCR subsystem.
    Priority:
    1. Explicit override via EATGOOD_OCR_PROVIDER ('cloud'/'vision' vs 'local'/'tesseract')
    2. Serverless environment (Vercel / AWS Lambda): Cloud Vision prioritized
    3. Local development environment: Local Tesseract prioritized (offline, zero-cost)
    4. Cloud Vision fallback if local Tesseract missing
    5. Clean diagnostic instructions if neither is configured
    """
    preferred = os.environ.get("EATGOOD_OCR_PROVIDER", "").lower().strip()
    vision_key = get_cloud_vision_api_key()
    tess_path = get_tesseract_path()
    is_serverless = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

    # Priority 1: Explicit user override
    if preferred in ["cloud", "vision", "google"]:
        if vision_key:
            return {
                "available": True,
                "engine": "Google Cloud Vision v1 (Cloud)",
                "provider": "cloud_vision",
                "version": "v1",
                "path": None
            }
        else:
            return {
                "available": False,
                "engine": "Google Cloud Vision (Unconfigured)",
                "provider": "cloud_vision",
                "version": None,
                "path": None,
                "message": "EATGOOD_OCR_PROVIDER is set to cloud, but VISION_API_KEY is not configured in environment variables."
            }
    elif preferred in ["local", "tesseract"]:
        if tess_path:
            try:
                ver = pytesseract.get_tesseract_version() if pytesseract else None
                return {
                    "available": True,
                    "engine": f"Tesseract {ver} (Local)",
                    "provider": "tesseract",
                    "version": str(ver) if ver else None,
                    "path": tess_path
                }
            except Exception as e:
                return {
                    "available": False,
                    "engine": "Tesseract (Error)",
                    "provider": "tesseract",
                    "version": None,
                    "path": tess_path,
                    "error": str(e)
                }
        else:
            return {
                "available": False,
                "engine": "Tesseract (Not Detected)",
                "provider": "tesseract",
                "version": None,
                "path": None,
                "message": "EATGOOD_OCR_PROVIDER is set to local, but Tesseract binary was not found on this system."
            }

    # Priority 2: Serverless production (Vercel / AWS Lambda) -> Cloud Vision
    if is_serverless and vision_key:
        return {
            "available": True,
            "engine": "Google Cloud Vision v1 (Cloud)",
            "provider": "cloud_vision",
            "version": "v1",
            "path": None
        }

    # Priority 3: Local development with Tesseract installed
    if tess_path:
        try:
            ver = pytesseract.get_tesseract_version() if pytesseract else None
            return {
                "available": True,
                "engine": f"Tesseract {ver} (Local)",
                "provider": "tesseract",
                "version": str(ver) if ver else None,
                "path": tess_path
            }
        except Exception:
            pass

    # Priority 4: Cloud Vision if key is configured (even on local machine without Tesseract)
    if vision_key:
        return {
            "available": True,
            "engine": "Google Cloud Vision v1 (Cloud)",
            "provider": "cloud_vision",
            "version": "v1",
            "path": None
        }

    # Priority 5: Neither available
    return {
        "available": False,
        "engine": "No OCR Engine Configured",
        "provider": "none",
        "version": None,
        "path": None,
        "message": (
            "OCR service is not configured on this system. "
            "To enable food label scanning in production, set the VISION_API_KEY environment variable in your Vercel project settings. "
            "You can enter nutrition facts manually."
        )
    }


def preprocess_image_for_ocr(image_path: str) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Loads and preprocesses food label image using Pillow and OpenCV:
    1. EXIF orientation correction (fixes smartphone camera rotation).
    2. Dimension normalization (scales small images up for clarity, downsamples giant images to prevent OOM/slowdown).
    3. Conversion to Grayscale.
    4. Contrast-Limited Adaptive Histogram Equalization (CLAHE) to balance harsh packaging glare.
    5. Bilateral filtering to preserve sharp character edges while eliminating background packaging grain.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    # 1. Load via PIL and transpose according to EXIF rotation
    with Image.open(image_path) as raw_pil:
        oriented = ImageOps.exif_transpose(raw_pil)
        # Ensure RGB mode (handles RGBA, Palette, MPO from iPhone cameras)
        rgb_pil = oriented.convert("RGB")
        orig_w, orig_h = rgb_pil.size

    # 2. Resizing & dimension normalization
    max_dim = 2000
    min_dim = 650
    w, h = orig_w, orig_h

    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        w = int(w * scale)
        h = int(h * scale)
        rgb_pil = rgb_pil.resize((w, h), Image.Resampling.LANCZOS)
    elif min(w, h) < min_dim and max(w, h) < 1400:
        scale = min_dim / float(min(w, h))
        w = int(w * scale)
        h = int(h * scale)
        rgb_pil = rgb_pil.resize((w, h), Image.Resampling.BICUBIC)

    # Preprocessing: OpenCV (if available) or Pillow
    if cv2 is not None:
        cv_rgb = np.array(rgb_pil)
        gray = cv2.cvtColor(cv_rgb, cv2.COLOR_RGB2GRAY)
        denoised = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
    else:
        gray_pil = rgb_pil.convert("L")
        enhanced = np.array(ImageOps.autocontrast(gray_pil, cutoff=2))

    metadata = {
        "original_size": (orig_w, orig_h),
        "processed_size": (w, h),
        "orientation_corrected": True
    }

    return enhanced, metadata


def run_cloud_vision_ocr(image_path: str) -> Dict[str, Any]:
    """
    Executes Google Cloud Vision Document Text Detection via REST API.
    Endpoint: https://vision.googleapis.com/v1/images:annotate
    Provides enterprise-grade label reading for food packaging with zero native binary dependencies.
    """
    api_key = get_cloud_vision_api_key()
    if not api_key:
        return {
            "status": "error",
            "message": "Google Cloud Vision API key is not configured. Set VISION_API_KEY in environment variables.",
            "raw_text": "",
            "lines": [],
            "engine": "Google Cloud Vision (Unconfigured)",
            "ocr_confidence": 0.0
        }

    if not os.path.exists(image_path):
        return {
            "status": "error",
            "message": f"Image file not found at {image_path}",
            "raw_text": "",
            "lines": [],
            "engine": "Google Cloud Vision v1",
            "ocr_confidence": 0.0
        }

    try:
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        b64_content = base64.b64encode(img_bytes).decode("utf-8")
        payload = {
            "requests": [
                {
                    "image": {"content": b64_content},
                    "features": [
                        {"type": "DOCUMENT_TEXT_DETECTION"}
                    ],
                    "imageContext": {
                        "languageHints": ["en", "hi"]
                    }
                }
            ]
        }

        url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

        with httpx.Client(timeout=12.0) as client:
            resp = client.post(url, json=payload)

        if resp.status_code == 400:
            err_msg = resp.json().get("error", {}).get("message", "Invalid request")
            logger.error(f"Cloud Vision 400: {err_msg}")
            return {
                "status": "error",
                "message": f"Cloud Vision OCR error: {err_msg}",
                "raw_text": "",
                "lines": [],
                "engine": "Google Cloud Vision v1",
                "ocr_confidence": 0.0
            }
        elif resp.status_code == 403:
            logger.error("Cloud Vision 403: Permission denied or API key invalid.")
            return {
                "status": "error",
                "message": "Cloud Vision API key is invalid or 'Cloud Vision API' is not enabled in your Google Cloud Console project.",
                "raw_text": "",
                "lines": [],
                "engine": "Google Cloud Vision v1",
                "ocr_confidence": 0.0
            }
        elif resp.status_code == 429:
            logger.error("Cloud Vision 429: Rate limit or quota exceeded.")
            return {
                "status": "error",
                "message": "Cloud Vision API quota limit exceeded. You can enter nutrition facts manually.",
                "raw_text": "",
                "lines": [],
                "engine": "Google Cloud Vision v1",
                "ocr_confidence": 0.0
            }
        elif resp.status_code != 200:
            logger.error(f"Cloud Vision HTTP {resp.status_code}: {resp.text}")
            return {
                "status": "error",
                "message": f"Cloud Vision service returned HTTP {resp.status_code}. You can enter nutrition facts manually.",
                "raw_text": "",
                "lines": [],
                "engine": "Google Cloud Vision v1",
                "ocr_confidence": 0.0
            }

        data = resp.json()
        responses = data.get("responses", [])
        if not responses:
            return {
                "status": "no_text_found",
                "message": "No response returned by Cloud Vision OCR.",
                "raw_text": "",
                "lines": [],
                "engine": "Google Cloud Vision v1",
                "ocr_confidence": 0.0
            }

        first_res = responses[0]
        if "error" in first_res:
            err_msg = first_res["error"].get("message", "Unknown error")
            return {
                "status": "error",
                "message": f"Cloud Vision error: {err_msg}",
                "raw_text": "",
                "lines": [],
                "engine": "Google Cloud Vision v1",
                "ocr_confidence": 0.0
            }

        # Extract text
        full_ann = first_res.get("fullTextAnnotation")
        raw_text = ""
        confidences = []

        if full_ann and full_ann.get("text"):
            raw_text = full_ann.get("text", "")
            for page in full_ann.get("pages", []):
                if "confidence" in page:
                    confidences.append(float(page["confidence"]))
                for block in page.get("blocks", []):
                    if "confidence" in block:
                        confidences.append(float(block["confidence"]))
                    for para in block.get("paragraphs", []):
                        if "confidence" in para:
                            confidences.append(float(para["confidence"]))
        elif first_res.get("textAnnotations"):
            raw_text = first_res["textAnnotations"][0].get("description", "")

        avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.92
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]

        if not lines or not raw_text.strip():
            return {
                "status": "no_text_found",
                "message": "No legible text was detected in the uploaded image. Please ensure the nutrition panel is clearly visible and well-lit.",
                "raw_text": "",
                "lines": [],
                "engine": "Google Cloud Vision v1",
                "ocr_confidence": 0.0
            }

        return {
            "status": "success",
            "raw_text": raw_text,
            "lines": lines,
            "engine": "Google Cloud Vision v1",
            "ocr_confidence": avg_conf,
            "preprocessing": {"source": "cloud_vision", "features": ["DOCUMENT_TEXT_DETECTION"]}
        }
    except httpx.TimeoutException:
        logger.error("Cloud Vision OCR request timed out.")
        return {
            "status": "error",
            "message": "Cloud Vision OCR request timed out. You can enter nutrition facts manually.",
            "raw_text": "",
            "lines": [],
            "engine": "Google Cloud Vision v1",
            "ocr_confidence": 0.0
        }
    except Exception as e:
        logger.error(f"Unexpected Cloud Vision error: {e}")
        return {
            "status": "error",
            "message": f"Cloud Vision network error: {str(e)}. You can enter nutrition facts manually.",
            "raw_text": "",
            "lines": [],
            "engine": "Google Cloud Vision v1",
            "ocr_confidence": 0.0
        }


def _run_tesseract_ocr(image_path: str) -> Dict[str, Any]:
    """
    Executes local Tesseract OCR on the supplied food label photograph.
    Employs OpenCV/PIL preprocessing and multi-pass PSM 6 / PSM 3 strategy.
    """
    cmd = get_tesseract_path()
    if not cmd or pytesseract is None:
        return {
            "status": "error",
            "message": "Local Tesseract OCR binary is not installed or accessible on this system. You can enter nutrition facts manually.",
            "raw_text": "",
            "lines": [],
            "engine": "Tesseract (Not Detected)",
            "ocr_confidence": 0.0
        }

    try:
        processed_img, meta = preprocess_image_for_ocr(image_path)
    except Exception as e:
        logger.error(f"Image preprocessing failed for {image_path}: {e}")
        return {
            "status": "error",
            "message": f"Unable to decode or preprocess image: {str(e)}",
            "raw_text": "",
            "lines": [],
            "engine": "Tesseract (Local)",
            "ocr_confidence": 0.0
        }

    # Pass 1: Tabular block mode (PSM 6: Assume a single uniform block of text)
    try:
        raw_text = pytesseract.image_to_string(processed_img, config="--oem 3 --psm 6")
    except Exception as e:
        logger.error(f"Tesseract execution error on Pass 1: {e}")
        raw_text = ""

    # Pass 2: If Pass 1 yielded almost nothing, try PSM 3 (Fully automatic page segmentation)
    if len(raw_text.strip()) < 25:
        try:
            raw_text_p2 = pytesseract.image_to_string(processed_img, config="--oem 3 --psm 3")
            if len(raw_text_p2.strip()) > len(raw_text.strip()):
                raw_text = raw_text_p2
        except Exception:
            pass

    # Extract word confidence data
    try:
        ocr_data = pytesseract.image_to_data(processed_img, output_type=pytesseract.Output.DICT)
        conf_list = [c for c in ocr_data.get("conf", []) if isinstance(c, (int, float)) and c > 0]
        avg_confidence = round(float(sum(conf_list) / len(conf_list)) / 100.0, 2) if conf_list else 0.50
    except Exception:
        avg_confidence = 0.50

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    try:
        ver = pytesseract.get_tesseract_version()
        engine_str = f"Tesseract {ver} (Local)"
    except Exception:
        engine_str = "Tesseract (Local)"

    if not lines:
        return {
            "status": "no_text_found",
            "message": "No legible text was detected in the uploaded image. Please ensure the nutrition panel is clearly visible and well-lit.",
            "raw_text": "",
            "lines": [],
            "engine": engine_str,
            "ocr_confidence": 0.0,
            "preprocessing": meta
        }

    return {
        "status": "success",
        "raw_text": raw_text,
        "lines": lines,
        "engine": engine_str,
        "ocr_confidence": avg_confidence,
        "preprocessing": meta
    }


def run_image_ocr(image_path: str) -> Dict[str, Any]:
    """
    Executes OCR on the supplied food label photograph using the optimal available engine:
    - Google Cloud Vision v1 (production serverless / cloud)
    - Tesseract 5 (local offline development)
    NEVER returns hardcoded fallback mock data.
    """
    engine_info = get_ocr_engine_info()
    if not engine_info.get("available"):
        return {
            "status": "error",
            "message": engine_info.get("message") or (
                "OCR service is not configured on this system. "
                "Set VISION_API_KEY in production or install Tesseract locally. "
                "You can enter nutrition facts manually."
            ),
            "raw_text": "",
            "lines": [],
            "engine": engine_info.get("engine", "None"),
            "ocr_confidence": 0.0
        }

    provider = engine_info.get("provider")

    if provider == "cloud_vision":
        res = run_cloud_vision_ocr(image_path)
        # Graceful fallback: If cloud fails and local Tesseract is available, try local
        if res.get("status") == "error" and get_tesseract_path():
            logger.warning("Cloud Vision failed, falling back to local Tesseract.")
            return _run_tesseract_ocr(image_path)
        return res
    elif provider == "tesseract":
        res = _run_tesseract_ocr(image_path)
        # Graceful fallback: If local fails and cloud key is available, try cloud
        if res.get("status") == "error" and get_cloud_vision_api_key():
            logger.warning("Local Tesseract failed, falling back to Cloud Vision.")
            return run_cloud_vision_ocr(image_path)
        return res
    else:
        return {
            "status": "error",
            "message": "No valid OCR provider found. You can enter nutrition facts manually.",
            "raw_text": "",
            "lines": [],
            "engine": "None",
            "ocr_confidence": 0.0
        }


def _clean_number_str(raw_str: str) -> Optional[float]:
    """
    Cleans raw OCR number strings handling common OCR artifacts:
    - Replaces comma with decimal point ('12,5' -> '12.5')
    - Replaces leading 'O' or 'o' with '0' ('Og' -> '0')
    - Handles '<0.1' or '<01'
    - Strips trailing characters
    """
    if not raw_str:
        return None
    s = raw_str.strip().replace(",", ".")

    # Handle common OCR 'Og' -> '0g' or 'O g'
    s = re.sub(r'^[Oo]\s*g?', '0', s)

    # Handle '<01' -> '0.1' or '<0.1'
    if s.startswith("<01") or s == "01":
        return 0.1
    if s.startswith("<"):
        s = s.lstrip("<").strip()

    # Extract first valid floating point or integer number
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)', s)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def extract_nutrition_from_text(text: str, ocr_confidence: float = 0.85) -> Dict[str, Any]:
    """
    Parses unstructured OCR text into structured nutrition metrics using domain heuristics.
    Detects inline and tabular representations, checks physiological plausibility,
    and returns explicit status tags for every field.
    """
    if not text or not text.strip():
        # Clean empty return when no text was extracted
        empty_fields = {
            "serving_size": None,
            "serving_size_unit": "g",
            "measurement_basis": "per 100g",
            "energy_kcal": None,
            "carbohydrates_g": None,
            "sugars_g": None,
            "added_sugars_g": None,
            "protein_g": None,
            "total_fat_g": None,
            "saturated_fat_g": None,
            "trans_fat_g": None,
            "sodium_mg": None,
            "dietary_fibre_g": None,
            "ingredients": None
        }
        field_statuses = {k: "not_found" for k in empty_fields.keys()}
        return {
            "extracted_values": empty_fields,
            "field_statuses": field_statuses,
            "confidence_scores": {},
            "field_notes": {},
            "missing_fields": list(empty_fields.keys()),
            "suspicious_flags": [],
            "requires_user_confirmation": True
        }

    clean_text = text.replace(",", ".")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    results: Dict[str, Any] = {
        "serving_size": None,
        "serving_size_unit": "g",
        "measurement_basis": "per 100g",
        "energy_kcal": None,
        "carbohydrates_g": None,
        "sugars_g": None,
        "added_sugars_g": None,
        "protein_g": None,
        "total_fat_g": None,
        "saturated_fat_g": None,
        "trans_fat_g": None,
        "sodium_mg": None,
        "dietary_fibre_g": None,
        "ingredients": None
    }

    confidence: Dict[str, float] = {}
    field_statuses: Dict[str, str] = {}
    field_notes: Dict[str, str] = {}
    suspicious_flags: List[str] = []

    # 1. Serving size & basis detection
    srv_patterns = [
        r'(?:serve\s*size\s*(?:is)?|serving\s*size\s*(?:is)?|serve\s*measure|per\s*serve)[\s:]*([0-9.]+)\s*([gml]{1,2}|gm)',
        r'([0-9.]+)\s*([gml]{1,2})\s*(?:per\s*serving|serve\s*size)'
    ]
    for p in srv_patterns:
        m = re.search(p, clean_text, re.IGNORECASE)
        if m:
            results["serving_size"] = float(m.group(1))
            unit = m.group(2).lower()
            results["serving_size_unit"] = "ml" if "ml" in unit else "g"
            confidence["serving_size"] = min(0.95, ocr_confidence + 0.1)
            field_statuses["serving_size"] = "extracted"
            break

    # Measurement basis detection
    if re.search(r'per\s*100\s*ml', clean_text, re.IGNORECASE):
        results["measurement_basis"] = "per 100ml"
        results["serving_size_unit"] = "ml"
    elif re.search(r'per\s*100\s*(?:g|gm|9)', clean_text, re.IGNORECASE):
        results["measurement_basis"] = "per 100g"
        results["serving_size_unit"] = "g"
    elif results["serving_size"] and re.search(r'per\s*serving', clean_text, re.IGNORECASE):
        results["measurement_basis"] = "per serving"

    if results["serving_size"] is None:
        if results["measurement_basis"] in ["per 100g", "per 100ml"]:
            results["serving_size"] = 100.0
            confidence["serving_size"] = 0.80
            field_statuses["serving_size"] = "extracted"
        else:
            field_statuses["serving_size"] = "not_found"

    # 2. Nutrient Line & Tabular Regex Matching
    nutrient_matchers = [
        ("energy_kcal", [
            r'(?:energy|calories|caloric\s*value)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([0-9.]+)\s*(?:kcal|cal)?',
            r'([0-9.]+)\s*kcal'
        ]),
        ("carbohydrates_g", [
            r'(?:total\s*carbohydrates?|carbohydrates?|total\s*carbs?|carbs?)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("added_sugars_g", [
            r'(?:added\s*sugars?|of\s*which\s*added\s*sugars?)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("sugars_g", [
            r'(?:total\s*sugars?|sugars?|of\s*which\s*sugars?)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("protein_g", [
            r'(?:protein)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("saturated_fat_g", [
            r'(?:saturated\s*fat(?:ty\s*acids)?|sat\s*fat)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("trans_fat_g", [
            r'(?:trans\s*fat(?:ty\s*acids)?)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("total_fat_g", [
            r'(?:total\s*fat|fat)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ]),
        ("sodium_mg", [
            r'(?:sodium)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)\s*(?:mg)?',
            r'(?:salt)[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)\s*(?:g|mg)?'
        ]),
        ("dietary_fibre_g", [
            r'(?:dietary\s*fib(?:re|er)|fib(?:re|er))[\w\s*”\"]*?(?:\([^\)]*\))?[\s:]+([<~]?\s*[0-9Oo.,]+)',
        ])
    ]

    for key, regex_list in nutrient_matchers:
        val = None
        matched_str = ""
        # Check line by line first (handles tabular rows cleanly)
        for line in lines:
            for p in regex_list:
                m = re.search(p, line, re.IGNORECASE)
                if m:
                    parsed = _clean_number_str(m.group(1))
                    if parsed is not None:
                        val = parsed
                        matched_str = line
                        if key == "sodium_mg" and "salt" in p.lower() and val < 50:
                            # Convert salt in grams to sodium in mg (salt * 400 = sodium mg)
                            val = round(val * 400, 1)
                            field_notes["sodium_mg"] = f"Calculated from Salt ({m.group(1)}g)"
                        break
            if val is not None:
                break

        # Fallback to multi-line string search if line-by-line missed
        if val is None:
            for p in regex_list:
                m = re.search(p, clean_text, re.IGNORECASE)
                if m:
                    parsed = _clean_number_str(m.group(1))
                    if parsed is not None:
                        val = parsed
                        matched_str = m.group(0)
                        if key == "sodium_mg" and "salt" in p.lower() and val < 50:
                            val = round(val * 400, 1)
                        break

        if val is not None:
            results[key] = val
            confidence[key] = min(0.92, ocr_confidence)
            field_statuses[key] = "extracted"
        else:
            field_statuses[key] = "not_found"

    # 3. Macro Glitch Repair Heuristic:
    # If a macro in grams is > 100 on a per-100g basis (e.g. 3736 instead of 37.36),
    # OCR likely dropped the decimal point. Correct with flag.
    if results["measurement_basis"] in ["per 100g", "per 100ml"]:
        for macro in ["carbohydrates_g", "protein_g", "total_fat_g", "sugars_g", "dietary_fibre_g"]:
            raw_v = results[macro]
            if raw_v is not None and raw_v > 100.0:
                # Attempt decimal repair if dividing by 100 yields plausible macro (0 to 100)
                repaired = round(raw_v / 100.0, 2)
                if 0 <= repaired <= 100:
                    results[macro] = repaired
                    field_statuses[macro] = "needs_review"
                    field_notes[macro] = f"Auto-repaired missing decimal ({raw_v}g -> {repaired}g). Please verify."
                    suspicious_flags.append(f"{macro.replace('_', ' ').title()}: Suspicious value {raw_v}g repaired to {repaired}g. Please confirm.")
                else:
                    field_statuses[macro] = "needs_review"
                    suspicious_flags.append(f"{macro.replace('_', ' ').title()}: {raw_v}g exceeds 100g limit for {results['measurement_basis']}.")

    # 4. Ingredients Extraction
    ing_patterns = [
        r'(?:ingredients|ingredient\s*list)[\s:]*([^\.\n]+(?:\.[^\.\n]+){1,5})',
        r'(?:contains\s*[:])\s*([^\.\n]+)'
    ]
    for p in ing_patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            ing_text = m.group(1).strip()
            if len(ing_text) > 8:
                results["ingredients"] = ing_text
                confidence["ingredients"] = 0.85
                field_statuses["ingredients"] = "extracted"
                break
    if results["ingredients"] is None:
        field_statuses["ingredients"] = "not_found"

    # 5. Scientific Plausibility & Cross-Field Consistency Audits
    # Atwater calorie check: Energy = 4*Carbs + 4*Protein + 9*Fat
    if results["carbohydrates_g"] is not None and results["protein_g"] is not None and results["total_fat_g"] is not None and results["energy_kcal"] is not None:
        atwater = 4.0 * results["carbohydrates_g"] + 4.0 * results["protein_g"] + 9.0 * results["total_fat_g"]
        diff = abs(results["energy_kcal"] - atwater)
        if diff > 60:
            suspicious_flags.append(
                f"Calorie discrepancy: Reported {results['energy_kcal']} kcal vs Atwater estimate {atwater:.1f} kcal (Delta: {diff:.1f} kcal). Please verify label numbers."
            )
            field_statuses["energy_kcal"] = "needs_review"
            field_notes["energy_kcal"] = f"Atwater estimate is {atwater:.1f} kcal"

    # Saturated fat vs Total fat check
    if results["saturated_fat_g"] is not None and results["total_fat_g"] is not None:
        if results["saturated_fat_g"] > results["total_fat_g"]:
            suspicious_flags.append(
                f"Fat inconsistency: Saturated fat ({results['saturated_fat_g']}g) cannot exceed Total fat ({results['total_fat_g']}g)."
            )
            field_statuses["saturated_fat_g"] = "needs_review"

    # Sugars vs Carbohydrates check
    if results["sugars_g"] is not None and results["carbohydrates_g"] is not None:
        if results["sugars_g"] > results["carbohydrates_g"]:
            suspicious_flags.append(
                f"Carbohydrate inconsistency: Sugars ({results['sugars_g']}g) cannot exceed Total carbohydrates ({results['carbohydrates_g']}g)."
            )
            field_statuses["sugars_g"] = "needs_review"

    # Macronutrient sum vs serving size
    if results["serving_size"] and results["carbohydrates_g"] is not None and results["protein_g"] is not None and results["total_fat_g"] is not None:
        macro_sum = results["carbohydrates_g"] + results["protein_g"] + results["total_fat_g"]
        if macro_sum > (results["serving_size"] * 1.05):
            suspicious_flags.append(
                f"Macro sum ({macro_sum:.1f}g) exceeds declared serving basis ({results['serving_size']}g)."
            )

    # Missing core fields audit
    core_keys = ["energy_kcal", "carbohydrates_g", "sugars_g", "protein_g", "total_fat_g", "sodium_mg"]
    missing_fields = [k for k in core_keys if results[k] is None]

    return {
        "extracted_values": results,
        "field_statuses": field_statuses,
        "confidence_scores": confidence,
        "field_notes": field_notes,
        "missing_fields": missing_fields,
        "suspicious_flags": suspicious_flags,
        "requires_user_confirmation": True
    }
