import { useEffect, useRef, useState } from "react";

const TURNSTILE_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js";
const RECAPTCHA_SRC = "https://www.google.com/recaptcha/api.js";

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

/**
 * Cloudflare Turnstile widget, falling back to Google reCAPTCHA if
 * Turnstile is not configured or fails to load. Renders nothing if neither
 * key is configured (e.g. local development).
 */
export default function CaptchaWidget({ onVerify }) {
  const turnstileKey = import.meta.env.VITE_TURNSTILE_SITE_KEY;
  const recaptchaKey = import.meta.env.VITE_RECAPTCHA_SITE_KEY;
  const containerRef = useRef(null);
  const [provider, setProvider] = useState(turnstileKey ? "turnstile" : recaptchaKey ? "recaptcha" : null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!provider || !containerRef.current) return undefined;
    let cancelled = false;

    const render = async () => {
      try {
        if (provider === "turnstile") {
          await loadScript(TURNSTILE_SRC);
          if (cancelled || !window.turnstile) throw new Error("Turnstile unavailable");
          window.turnstile.render(containerRef.current, {
            sitekey: turnstileKey,
            callback: (token) => onVerify(token, "turnstile"),
            "error-callback": () => {
              if (recaptchaKey) setProvider("recaptcha");
              else setFailed(true);
            },
          });
        } else if (provider === "recaptcha") {
          await loadScript(RECAPTCHA_SRC);
          if (cancelled || !window.grecaptcha) throw new Error("reCAPTCHA unavailable");
          window.grecaptcha.render(containerRef.current, {
            sitekey: recaptchaKey,
            callback: (token) => onVerify(token, "recaptcha"),
          });
        }
      } catch {
        if (provider === "turnstile" && recaptchaKey) {
          setProvider("recaptcha");
        } else {
          setFailed(true);
        }
      }
    };

    render();
    return () => {
      cancelled = true;
    };
  }, [provider]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!provider) return null;
  if (failed) return <p className="form-hint">Captcha failed to load. Please refresh the page.</p>;

  return <div ref={containerRef} className="captcha-widget" />;
}
