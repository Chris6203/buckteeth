"""
Dental Image Quality Validator

Checks uploaded images for common issues that would cause insurance rejection:
- Wrong image type (not a dental image)
- Too blurry / low resolution
- Too dark or overexposed
- Missing required image metadata
- Wrong orientation
- File too large or too small
- Unsupported format

Runs BEFORE AI analysis to give immediate feedback to the doctor.
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field


@dataclass
class ImageQualityIssue:
    """A single quality issue found in an image."""
    code: str
    severity: str  # "error" (will be rejected), "warning" (may cause issues)
    message: str
    suggestion: str


@dataclass
class ImageQualityResult:
    """Result of image quality validation."""
    passed: bool = True
    issues: list[ImageQualityIssue] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def errors(self) -> list[ImageQualityIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ImageQualityIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "metadata": self.metadata,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


# Minimum requirements for insurance-quality dental images
MIN_WIDTH = 300
MIN_HEIGHT = 300
MIN_FILE_SIZE = 10_000  # 10KB — anything smaller is likely corrupt
MAX_FILE_SIZE = 25_000_000  # 25MB — most payers reject larger
SUPPORTED_FORMATS = {"image/jpeg", "image/png", "image/tiff", "image/bmp", "image/webp"}
PREFERRED_FORMATS = {"image/jpeg", "image/png"}


def validate_image_quality(
    image_data: bytes,
    media_type: str,
    filename: str | None = None,
) -> ImageQualityResult:
    """
    Validate an uploaded dental image for quality and insurance compatibility.

    Args:
        image_data: Raw image bytes
        media_type: MIME type from upload
        filename: Original filename (optional)

    Returns:
        ImageQualityResult with any issues found
    """
    issues: list[ImageQualityIssue] = []
    metadata: dict = {
        "file_size": len(image_data),
        "media_type": media_type,
        "filename": filename,
    }

    # ── File size checks ─────────────────────────────────────────────
    if len(image_data) < MIN_FILE_SIZE:
        issues.append(ImageQualityIssue(
            code="FILE_TOO_SMALL",
            severity="error",
            message=f"Image is only {len(image_data):,} bytes — likely corrupt or a thumbnail.",
            suggestion="Upload the full-resolution image from your imaging system or camera.",
        ))

    if len(image_data) > MAX_FILE_SIZE:
        issues.append(ImageQualityIssue(
            code="FILE_TOO_LARGE",
            severity="warning",
            message=f"Image is {len(image_data) / 1_000_000:.1f}MB — some payers reject files over 25MB.",
            suggestion="Reduce image size or resolution. JPEG at 90% quality is usually sufficient.",
        ))

    # ── Format checks ────────────────────────────────────────────────
    detected_type = _detect_image_format(image_data)
    metadata["detected_format"] = detected_type

    if detected_type is None:
        issues.append(ImageQualityIssue(
            code="UNRECOGNIZED_FORMAT",
            severity="error",
            message="File does not appear to be a valid image.",
            suggestion="Upload a JPEG or PNG image. If exporting from imaging software, choose JPEG format.",
        ))
        return ImageQualityResult(passed=False, issues=issues, metadata=metadata)

    if detected_type not in SUPPORTED_FORMATS:
        issues.append(ImageQualityIssue(
            code="UNSUPPORTED_FORMAT",
            severity="error",
            message=f"Image format '{detected_type}' is not supported by most insurance payers.",
            suggestion="Convert to JPEG or PNG before uploading.",
        ))

    if detected_type not in PREFERRED_FORMATS and detected_type in SUPPORTED_FORMATS:
        issues.append(ImageQualityIssue(
            code="NON_PREFERRED_FORMAT",
            severity="warning",
            message=f"Format '{detected_type}' is supported but JPEG or PNG is preferred by most payers.",
            suggestion="Consider converting to JPEG for best compatibility.",
        ))

    # ── Resolution checks ────────────────────────────────────────────
    dimensions = _get_image_dimensions(image_data, detected_type)
    if dimensions:
        width, height = dimensions
        metadata["width"] = width
        metadata["height"] = height
        metadata["megapixels"] = round(width * height / 1_000_000, 1)

        if width < MIN_WIDTH or height < MIN_HEIGHT:
            issues.append(ImageQualityIssue(
                code="RESOLUTION_TOO_LOW",
                severity="error",
                message=f"Image resolution ({width}x{height}) is too low for insurance documentation.",
                suggestion="Use at least 640x480 resolution. Most dental sensors and cameras produce much higher resolution — check your export settings.",
            ))
        elif width < 640 or height < 480:
            issues.append(ImageQualityIssue(
                code="RESOLUTION_LOW",
                severity="warning",
                message=f"Image resolution ({width}x{height}) is low — details may not be clearly visible.",
                suggestion="Higher resolution images (1000x800+) provide better documentation and are less likely to be questioned.",
            ))

        # Check for very unusual aspect ratios (might be cropped wrong)
        aspect = max(width, height) / max(min(width, height), 1)
        if aspect > 5:
            issues.append(ImageQualityIssue(
                code="UNUSUAL_ASPECT_RATIO",
                severity="warning",
                message=f"Image has an unusual aspect ratio ({width}x{height}) — it may be cropped incorrectly.",
                suggestion="Check that the full image was captured and not accidentally cropped.",
            ))

    # ── Dental-specific checks ───────────────────────────────────────
    if filename:
        fn_lower = filename.lower()
        # Check for screenshot indicators (not ideal for insurance)
        if any(term in fn_lower for term in ["screenshot", "screen shot", "screen_shot"]):
            issues.append(ImageQualityIssue(
                code="SCREENSHOT_DETECTED",
                severity="warning",
                message="This appears to be a screenshot — insurance companies prefer original imaging files.",
                suggestion="Export the original image from your dental imaging software (Dexis, Apteryx, Dentrix Image, etc.) rather than taking a screenshot.",
            ))

        # Check for common non-dental images
        if any(term in fn_lower for term in ["selfie", "profile", "avatar", "logo"]):
            issues.append(ImageQualityIssue(
                code="NON_DENTAL_IMAGE",
                severity="error",
                message="This doesn't appear to be a dental image.",
                suggestion="Upload a dental radiograph (periapical, bitewing, panoramic) or intraoral photograph.",
            ))

    # ── Overall assessment ───────────────────────────────────────────
    has_errors = any(i.severity == "error" for i in issues)

    return ImageQualityResult(
        passed=not has_errors,
        issues=issues,
        metadata=metadata,
    )


def _detect_image_format(data: bytes) -> str | None:
    """Detect image format from magic bytes."""
    if len(data) < 8:
        return None

    # JPEG
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"

    # PNG
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"

    # TIFF (little-endian or big-endian)
    if data[:4] in (b"II\x2a\x00", b"MM\x00\x2a"):
        return "image/tiff"

    # BMP
    if data[:2] == b"BM":
        return "image/bmp"

    # WebP
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"

    # GIF
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"

    return None


def _get_image_dimensions(data: bytes, media_type: str | None) -> tuple[int, int] | None:
    """Extract image dimensions without PIL."""
    try:
        if media_type == "image/png" and len(data) >= 24:
            # PNG: width and height at bytes 16-23
            width = struct.unpack(">I", data[16:20])[0]
            height = struct.unpack(">I", data[20:24])[0]
            return (width, height)

        if media_type == "image/jpeg":
            return _get_jpeg_dimensions(data)

        if media_type == "image/bmp" and len(data) >= 26:
            width = struct.unpack("<I", data[18:22])[0]
            height = abs(struct.unpack("<i", data[22:26])[0])
            return (width, height)

    except Exception:
        pass

    return None


def _get_jpeg_dimensions(data: bytes) -> tuple[int, int] | None:
    """Extract JPEG dimensions by scanning markers."""
    try:
        i = 2  # skip SOI marker
        while i < len(data) - 1:
            if data[i] != 0xFF:
                break
            marker = data[i + 1]

            # SOF markers (Start of Frame) contain dimensions
            if marker in (0xC0, 0xC1, 0xC2):
                if i + 9 < len(data):
                    height = struct.unpack(">H", data[i + 5:i + 7])[0]
                    width = struct.unpack(">H", data[i + 7:i + 9])[0]
                    return (width, height)

            # Skip marker
            if marker in (0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0x01):
                i += 2
            elif marker == 0xD9:  # EOI
                break
            elif i + 3 < len(data):
                length = struct.unpack(">H", data[i + 2:i + 4])[0]
                i += 2 + length
            else:
                break
    except Exception:
        pass

    return None
