import { useEffect, useState } from "react";

import conventionClient from "../api/conventionClient";
import { extractErrorMessage } from "../constants";

export default function AdminConvention() {
  const [name, setName] = useState("");
  const [savedName, setSavedName] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [formError, setFormError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    conventionClient
      .get("/")
      .then(({ data }) => {
        setName(data.name);
        setSavedName(data.name);
      })
      .catch((err) => setLoadError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    setMessage("");
    setSaving(true);
    try {
      const { data } = await conventionClient.patch("/", { name });
      setName(data.name);
      setSavedName(data.name);
      setMessage("Convention name updated.");
    } catch (err) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="page page-narrow">
      <h1>Convention</h1>

      {loading && <p className="page-loading">Loading...</p>}
      {loadError && <p className="form-error">{loadError}</p>}

      {!loading && !loadError && (
        <form className="form" onSubmit={handleSubmit}>
          <label>
            Convention name
            <input
              type="text"
              name="name"
              required
              maxLength={100}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          </label>

          <p className="form-hint">Current: {savedName}</p>

          {message && <p className="form-success">{message}</p>}
          {formError && <p className="form-error">{formError}</p>}

          <div>
            <button type="submit" className="button" disabled={saving || name === savedName}>
              {saving ? "Saving..." : "Save changes"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
