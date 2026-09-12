import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import CaptchaWidget from "../components/CaptchaWidget";
import { useAuth } from "../context/AuthContext";
import { DROPOFF_LOCATIONS, PAYMENT_PREFERENCES, extractErrorMessage } from "../constants";

const initialState = {
  email: "",
  password: "",
  confirm_password: "",
  first_name: "",
  last_name: "",
  phone_number: "",
  dropoff_location: DROPOFF_LOCATIONS[0].value,
  payment_preference: PAYMENT_PREFERENCES[0].value,
};

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(initialState);
  const [captcha, setCaptcha] = useState({ token: "", provider: "turnstile" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await register({
        ...form,
        phone_number: form.phone_number.trim(),
        captcha_token: captcha.token,
        captcha_provider: captcha.provider,
      });
      navigate("/account-pending", { state: { email: form.email } });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page page-narrow">
      <h1>Create an account</h1>
      <form className="form" onSubmit={handleSubmit}>
        <label>
          Email
          <input type="email" name="email" required value={form.email} onChange={handleChange} />
        </label>
        <label>
          First name
          <input type="text" name="first_name" required value={form.first_name} onChange={handleChange} />
        </label>
        <label>
          Last name
          <input type="text" name="last_name" required value={form.last_name} onChange={handleChange} />
        </label>
        <label>
          Phone number
          <input
            type="tel"
            name="phone_number"
            required
            placeholder="+14155552671"
            value={form.phone_number}
            onChange={handleChange}
          />
        </label>
        <label>
          Dropoff location
          <select name="dropoff_location" value={form.dropoff_location} onChange={handleChange}>
            {DROPOFF_LOCATIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Payment preference
          <select name="payment_preference" value={form.payment_preference} onChange={handleChange}>
            {PAYMENT_PREFERENCES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            required
            value={form.password}
            onChange={handleChange}
          />
        </label>
        <label>
          Confirm password
          <input
            type="password"
            name="confirm_password"
            required
            value={form.confirm_password}
            onChange={handleChange}
          />
        </label>

        <CaptchaWidget onVerify={(token, provider) => setCaptcha({ token, provider })} />

        {error && <p className="form-error">{error}</p>}

        <button type="submit" className="button" disabled={submitting}>
          {submitting ? "Creating account..." : "Register"}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
