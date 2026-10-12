"""Response headers that protect privacy and limit what the page can do."""
from flask import Flask, Response, request

# Everything is served from this origin: no CDNs, fonts, or third-party scripts.
# Camera frames never leave the browser in this phase, so connect-src is 'self'.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "media-src 'self' blob:",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


def register_security_headers(app: Flask) -> None:
    @app.after_request
    def add_headers(response: Response) -> Response:
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        # Allow the camera for this origin only; deny other powerful features.
        response.headers.setdefault(
            "Permissions-Policy", "camera=(self), microphone=(), geolocation=()"
        )
        # Pages and API responses may later contain personal data: never cache.
        if not request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response
