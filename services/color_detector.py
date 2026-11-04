import cv2
import numpy as np
import base64
import io
from PIL import Image

class ColorDetectorService:
    """
    Computer Vision service for extracting colorimetric sensor response.
    
    Technical Architecture:
    - Extracts central Region of Interest (ROI) to avoid edge shadows & glare.
    - Computes average & dominant RGB values within the sensor region.
    - Converts RGB to HSV and perceptual CIELAB (L*, a*, b*) color space.
    - Generates ROI visualization overlays.
    """

    @staticmethod
    def rgb_to_cielab(r: int, g: int, b: int):
        """
        Converts standard 8-bit sRGB to CIELAB (L*, a*, b*) using OpenCV.
        Returns: (L*, a*, b*) as floats.
        """
        # Create a 1x1 BGR pixel array
        pixel_bgr = np.uint8([[[b, g, r]]])
        # cv2.cvtColor to LAB returns L in [0, 255], A in [0, 255], B in [0, 255]
        # Standard CIE conversion scales: L* = L * 100 / 255, a* = A - 128, b* = B - 128
        pixel_lab = cv2.cvtColor(pixel_bgr, cv2.COLOR_BGR2Lab)[0][0]
        
        lab_l = round(float(pixel_lab[0]) * 100.0 / 255.0, 2)
        lab_a = round(float(pixel_lab[1]) - 128.0, 2)
        lab_b = round(float(pixel_lab[2]) - 128.0, 2)
        
        return lab_l, lab_a, lab_b

    @staticmethod
    def rgb_to_hsv(r: int, g: int, b: int):
        """
        Converts RGB to HSV.
        Returns: (H in [0, 360], S in [0, 100]%, V in [0, 100]%)
        """
        pixel_bgr = np.uint8([[[b, g, r]]])
        pixel_hsv = cv2.cvtColor(pixel_bgr, cv2.COLOR_BGR2HSV)[0][0]
        
        h = round(float(pixel_hsv[0]) * 2.0, 1)        # OpenCV H is 0-179 -> scaled to 0-360
        s = round(float(pixel_hsv[1]) * 100.0 / 255.0, 1) # 0-100%
        v = round(float(pixel_hsv[2]) * 100.0 / 255.0, 1) # 0-100%
        
        return h, s, v

    @classmethod
    def process_image(cls, image_bytes: bytes, roi_fraction: float = 0.45):
        """
        Processes an image from bytes (camera capture or file upload).
        Extracts sensor color from central ROI, calculates color spaces,
        and creates an annotated visualization image.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Unable to decode image. Please provide a valid JPEG or PNG file.")

        h, w, _ = img.shape

        # Define Central Region of Interest (ROI)
        # Taking central 45% to minimize peripheral lighting distortion
        margin_y = int(h * (1.0 - roi_fraction) / 2.0)
        margin_x = int(w * (1.0 - roi_fraction) / 2.0)
        
        y1, y2 = max(0, margin_y), min(h, h - margin_y)
        x1, x2 = max(0, margin_x), min(w, w - margin_x)
        
        roi = img[y1:y2, x1:x2]

        if roi.size == 0:
            raise ValueError("Invalid Region of Interest dimension.")

        # Compute average color in BGR
        avg_bgr = cv2.mean(roi)[:3]
        b = int(round(avg_bgr[0]))
        g = int(round(avg_bgr[1]))
        r = int(round(avg_bgr[2]))

        # Calculate CIELAB and HSV
        lab_l, lab_a, lab_b = cls.rgb_to_cielab(r, g, b)
        h_val, s_val, v_val = cls.rgb_to_hsv(r, g, b)

        # Draw ROI overlay on annotated image
        annotated = img.copy()
        # Draw bounding box around ROI
        cv2.rectangle(annotated, (x1, y2), (x2, y1), (6, 182, 212), 3) # Cyan highlight
        
        # Corner brackets for futuristic reticle
        corner_len = int(min(w, h) * 0.05)
        # Top-left
        cv2.line(annotated, (x1, y1), (x1 + corner_len, y1), (20, 184, 166), 4)
        cv2.line(annotated, (x1, y1), (x1, y1 + corner_len), (20, 184, 166), 4)
        # Top-right
        cv2.line(annotated, (x2, y1), (x2 - corner_len, y1), (20, 184, 166), 4)
        cv2.line(annotated, (x2, y1), (x2, y1 + corner_len), (20, 184, 166), 4)
        # Bottom-left
        cv2.line(annotated, (x1, y2), (x1 + corner_len, y2), (20, 184, 166), 4)
        cv2.line(annotated, (x1, y2), (x1, y2 - corner_len), (20, 184, 166), 4)
        # Bottom-right
        cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), (20, 184, 166), 4)
        cv2.line(annotated, (x2, y2), (x2, y2 - corner_len), (20, 184, 166), 4)

        # Draw sampled color patch at top-left corner
        patch_size = 60
        cv2.rectangle(annotated, (15, 15), (15 + patch_size, 15 + patch_size), (b, g, r), -1)
        cv2.rectangle(annotated, (15, 15), (15 + patch_size, 15 + patch_size), (255, 255, 255), 2)
        cv2.putText(annotated, f"RGB: {r},{g},{b}", (85, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(annotated, f"ROI Sample", (85, 65), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (6, 182, 212), 1, cv2.LINE_AA)

        # Encode annotated image back to base64 JPEG
        _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
        annotated_base64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "r": r,
            "g": g,
            "b": b,
            "hex": f"#{r:02x}{g:02x}{b:02x}",
            "lab": {
                "l": lab_l,
                "a": lab_a,
                "b": lab_b
            },
            "hsv": {
                "h": h_val,
                "s": s_val,
                "v": v_val
            },
            "annotated_image": f"data:image/jpeg;base64,{annotated_base64}"
        }

    @classmethod
    def process_base64(cls, base64_str: str):
        """Processes base64 encoded data URI string (e.g. from webcam canvas)."""
        if ',' in base64_str:
            base64_str = base64_str.split(',', 1)[1]
        image_bytes = base64.b64decode(base64_str)
        return cls.process_image(image_bytes)

    @classmethod
    def process_rgb_direct(cls, r: int, g: int, b: int):
        """
        Directly processes RGB values (e.g. directly passed from the Digital Sensor Simulator).
        Calculates LAB, HSV, and creates a swatch preview.
        """
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))

        lab_l, lab_a, lab_b = cls.rgb_to_cielab(r, g, b)
        h_val, s_val, v_val = cls.rgb_to_hsv(r, g, b)

        # Generate a clean simulated swatch image
        swatch = np.full((180, 180, 3), (b, g, r), dtype=np.uint8)
        # Add subtle inner border
        cv2.rectangle(swatch, (0, 0), (179, 179), (40, 50, 70), 2)
        
        _, buffer = cv2.imencode('.jpg', swatch, [cv2.IMWRITE_JPEG_QUALITY, 90])
        swatch_base64 = base64.b64encode(buffer).decode('utf-8')

        return {
            "r": r,
            "g": g,
            "b": b,
            "hex": f"#{r:02x}{g:02x}{b:02x}",
            "lab": {
                "l": lab_l,
                "a": lab_a,
                "b": lab_b
            },
            "hsv": {
                "h": h_val,
                "s": s_val,
                "v": v_val
            },
            "annotated_image": f"data:image/jpeg;base64,{swatch_base64}"
        }
