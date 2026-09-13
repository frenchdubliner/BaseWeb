import { useEffect, useState } from "react";

import listingsClient from "../api/listingsClient";
import { GAME_CONDITIONS, PET_EXPOSURE_OPTIONS, extractErrorMessage } from "../constants";

const emptyForm = {
  game_name: "",
  price: "",
  condition: GAME_CONDITIONS[0].value,
  has_missing_pieces: false,
  smoking_household: false,
  musty_smell: false,
  pet_exposure: "",
};

function conditionLabel(value) {
  return GAME_CONDITIONS.find((option) => option.value === value)?.label || value;
}

function petExposureLabel(value) {
  return PET_EXPOSURE_OPTIONS.find((option) => option.value === value)?.label || value;
}

export default function MyGames() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const [csvFile, setCsvFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState("");

  const loadListings = () => {
    setLoading(true);
    listingsClient
      .get("/")
      .then(({ data }) => setListings(data))
      .catch((err) => setLoadError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadListings();
  }, []);

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  };

  const startEdit = (listing) => {
    setEditingId(listing.id);
    setForm({
      game_name: listing.game_name,
      price: listing.price,
      condition: listing.condition,
      has_missing_pieces: listing.has_missing_pieces,
      smoking_household: listing.smoking_household,
      musty_smell: listing.musty_smell,
      pet_exposure: listing.pet_exposure,
    });
    setFormError("");
  };

  const cancelEdit = () => {
    setEditingId(null);
    setForm(emptyForm);
    setFormError("");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError("");
    setSubmitting(true);
    try {
      if (editingId) {
        const { data } = await listingsClient.patch(`/${editingId}/`, form);
        setListings((prev) => prev.map((item) => (item.id === editingId ? data : item)));
      } else {
        const { data } = await listingsClient.post("/", form);
        setListings((prev) => [data, ...prev]);
      }
      cancelEdit();
    } catch (err) {
      setFormError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Delete this game listing? This cannot be undone.")) return;
    try {
      await listingsClient.delete(`/${id}/`);
      setListings((prev) => prev.filter((item) => item.id !== id));
      if (editingId === id) cancelEdit();
    } catch (err) {
      setLoadError(extractErrorMessage(err));
    }
  };

  const handleDownloadTemplate = async () => {
    setUploadError("");
    try {
      const response = await listingsClient.get("/csv-template/", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.download = "game_listings_template.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setUploadError(extractErrorMessage(err));
    }
  };

  const handleCsvFileChange = (event) => {
    setCsvFile(event.target.files[0] || null);
    setUploadResult(null);
    setUploadError("");
  };

  const handleCsvUpload = async (event) => {
    event.preventDefault();
    if (!csvFile) return;
    setUploading(true);
    setUploadError("");
    setUploadResult(null);

    const formData = new FormData();
    formData.append("file", csvFile);

    try {
      const { data } = await listingsClient.post("/bulk-upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadResult(data);
      setCsvFile(null);
      event.target.reset();
      if (data.created_count > 0) {
        loadListings();
      }
    } catch (err) {
      setUploadError(extractErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const selectedCondition = GAME_CONDITIONS.find((option) => option.value === form.condition);

  return (
    <div className="page">
      <h1>My Games</h1>

      <form className="form" onSubmit={handleSubmit}>
        <h2>{editingId ? "Edit game" : "List a game for sale"}</h2>

        <label>
          Game name
          <input
            type="text"
            name="game_name"
            required
            value={form.game_name}
            onChange={handleChange}
          />
        </label>

        <label>
          Price ($)
          <input
            type="number"
            name="price"
            required
            min="0"
            step="0.01"
            value={form.price}
            onChange={handleChange}
          />
        </label>

        <label>
          Condition
          <select name="condition" value={form.condition} onChange={handleChange}>
            {GAME_CONDITIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        {selectedCondition && <p className="form-hint">{selectedCondition.description}</p>}

        <label className="checkbox-label">
          <input
            type="checkbox"
            name="has_missing_pieces"
            checked={form.has_missing_pieces}
            onChange={handleChange}
          />
          Has missing pieces?
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            name="smoking_household"
            checked={form.smoking_household}
            onChange={handleChange}
          />
          Exposed to smoking household?
        </label>

        <label className="checkbox-label">
          <input
            type="checkbox"
            name="musty_smell"
            checked={form.musty_smell}
            onChange={handleChange}
          />
          Has musty smell?
        </label>

        <label>
          Pet exposure
          <select name="pet_exposure" value={form.pet_exposure} onChange={handleChange}>
            {PET_EXPOSURE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        {formError && <p className="form-error">{formError}</p>}

        <div>
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Saving..." : editingId ? "Save changes" : "Add game"}
          </button>
          {editingId && (
            <button type="button" className="button button-secondary" onClick={cancelEdit}>
              Cancel
            </button>
          )}
        </div>
      </form>

      <div className="card">
        <h2>Bulk import from CSV</h2>
        <p className="form-hint">
          Upload a CSV file to add multiple games at once. Not sure of the format? Download the
          example file below - it explains every column and includes 10 sample rows you can
          upload as-is to see how it works.
        </p>
        <div>
          <button type="button" className="button button-secondary" onClick={handleDownloadTemplate}>
            Download example CSV
          </button>
        </div>

        <form className="form" onSubmit={handleCsvUpload}>
          <label>
            CSV file
            <input type="file" accept=".csv,text/csv" onChange={handleCsvFileChange} />
          </label>
          <div>
            <button type="submit" className="button" disabled={!csvFile || uploading}>
              {uploading ? "Uploading..." : "Upload CSV"}
            </button>
          </div>
        </form>

        {uploadError && <p className="form-error">{uploadError}</p>}

        {uploadResult && (
          <div className={uploadResult.error_count > 0 ? "form-error" : "form-success"}>
            <p>
              {uploadResult.created_count} game{uploadResult.created_count === 1 ? "" : "s"} imported
              successfully.
              {uploadResult.error_count > 0 &&
                ` ${uploadResult.error_count} row(s) had errors and were skipped:`}
            </p>
            {uploadResult.error_count > 0 && (
              <ul className="csv-error-list">
                {uploadResult.errors.map((rowError) => (
                  <li key={rowError.row}>
                    Row {rowError.row} ({rowError.game_name || "unnamed"}):{" "}
                    {Object.entries(rowError.errors)
                      .map(
                        ([field, messages]) =>
                          `${field}: ${Array.isArray(messages) ? messages.join(", ") : messages}`
                      )
                      .join("; ")}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <h2>Your listings</h2>
      {loading && <p className="page-loading">Loading...</p>}
      {loadError && <p className="form-error">{loadError}</p>}
      {!loading && listings.length === 0 && <p>You haven&apos;t listed any games yet.</p>}

      <div className="listings-grid">
        {listings.map((listing) => (
          <div className="card listing-card" key={listing.id}>
            <div className="listing-card-header">
              <strong>{listing.game_name}</strong>
              <span>${Number(listing.price).toFixed(2)}</span>
            </div>
            <p className="form-hint">{conditionLabel(listing.condition)}</p>
            <ul className="listing-flags">
              {listing.has_missing_pieces && <li>Missing pieces</li>}
              {listing.smoking_household && <li>Smoking household</li>}
              {listing.musty_smell && <li>Musty smell</li>}
              {listing.pet_exposure && <li>Pet exposure: {petExposureLabel(listing.pet_exposure)}</li>}
            </ul>
            <div>
              <button type="button" className="button" onClick={() => startEdit(listing)}>
                Edit
              </button>
              <button
                type="button"
                className="button button-secondary"
                onClick={() => handleDelete(listing.id)}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
